"""RAG Pipeline using LangGraph for orchestration.

This module implements the complete RAG workflow using LangGraph's state management.
"""
import os
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, NotRequired, Optional, Protocol, TypedDict, cast

from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

from app.core.rag_config import get_rag_config
from app.rag.embeddings.embedding_manager import EmbeddingManager
from app.rag.prompts.prompt_builder import PromptBuilder
from app.rag.rerankers.reranker_manager import RerankerManager
from app.rag.retrievers.retriever_manager import RetrieverManager

# Load backend/.env regardless of the directory from which Uvicorn is started
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger(__name__)

_YOUTUBE_QUERY_TERMS = ("youtube", "video", "transcript", "uploaded video")

# Define the state schema
class RAGState(TypedDict):
    """State schema for the RAG pipeline."""

    question: str
    embedding: Optional[List[float]]
    retrieved_docs: List[tuple]
    reranked_docs: List[tuple]
    context_documents: NotRequired[List[tuple]]
    prompt: str
    messages: List[Dict[str, str]]
    history: NotRequired[List[Dict[str, str]]]
    response: str
    metadata: Dict


class CompiledRAGGraph(Protocol):
    """The callable surface used from a compiled LangGraph workflow."""

    def invoke(self, state: RAGState) -> RAGState: ...


class RAGPipeline:
    """Complete RAG pipeline using LangGraph."""

    def __init__(
        self,
        collection_name: str = "rag_documents",
        llm_model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize the RAG pipeline.

        Args:
            collection_name: Name of the vector store collection
            llm_model: LLM model name
            temperature: LLM temperature
            max_tokens: Maximum tokens for generation
            api_key: Groq API key (defaults to environment)
        """
        rag_config = get_rag_config()

        # Get API key
        api_key = api_key or os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "Groq API key is required. Set the GROQ_API_KEY environment variable."
            )
            
        # Initialize LLM using ChatGroq
        self.llm = ChatGroq(
            model=llm_model or "openai/gpt-oss-120b",
            api_key=api_key,
            temperature=rag_config.temperature if temperature is None else temperature,
            max_tokens=rag_config.max_tokens if max_tokens is None else max_tokens,
        )

        # Initialize components
        self.embedding_manager = EmbeddingManager(api_key=api_key)
        self.retriever = RetrieverManager(
            collection_name=collection_name, embedding_manager=self.embedding_manager
        )
        self.reranker = None
        self.prompt_builder = PromptBuilder()

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledRAGGraph:
        """Build the LangGraph workflow."""
        # Create workflow
        workflow = StateGraph(RAGState)

        # Add nodes
        workflow.add_node("embed_question", self._embed_question)
        workflow.add_node("retrieve", self._retrieve_documents)
        workflow.add_node("rerank", self._rerank_documents)
        workflow.add_node("create_prompt", self._create_prompt)
        workflow.add_node("generate_response", self._generate_response)

        # Define edges (pipeline flow)
        workflow.set_entry_point("embed_question")
        workflow.add_edge("embed_question", "retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "create_prompt")
        workflow.add_edge("create_prompt", "generate_response")
        workflow.add_edge("generate_response", END)

        # Compile the graph
        return cast(CompiledRAGGraph, workflow.compile())

    def _embed_question(self, state: RAGState) -> RAGState:
        """Embed the user's question."""
        question = state["question"]
        embedding = self.embedding_manager.embed_query(question)

        logger.info("[RAG] Query embedding generated (dimension=%d)", len(embedding))

        return {
            **state,
            "embedding": embedding,
            "metadata": {**state.get("metadata", {}), "embedding_dim": len(embedding)},
        }

    def _retrieve_documents(self, state: RAGState) -> RAGState:
        """Retrieve documents while preserving their text for prompt construction."""
        question = state["question"]

        # Chroma's similarity_search_with_score returns a distance:
        # lower distance = better semantic match.
        relevance_threshold = 1.30

        metadata = state.get("metadata", {})
        requested_k = metadata.get("top_k")
        if requested_k is None:
            requested_k = get_rag_config().top_k_retrieval
        requested_k = int(requested_k)
        retrieval_errors = []
        authorized_source_ids = metadata.get("authorized_source_ids")
        filter_dict = None
        if authorized_source_ids is not None:
            clauses: list[dict[str, str]] = []
            field_map = {
                "document": "document_id",
                "website": "website_id",
                "youtube": "youtube_source_id",
            }
            for source_type, field in field_map.items():
                for source_id in authorized_source_ids.get(source_type, []):
                    clauses.append({field: str(source_id)})
                    # Legacy chunks only have source_id; include it in the
                    # same server-side Chroma predicate.
                    clauses.append({"source_id": str(source_id)})
            active_types = [
                source_type
                for source_type in field_map
                if authorized_source_ids.get(source_type)
            ]
            if not clauses:
                retrieved_docs = []
            elif len(active_types) > 1:
                # Each modality can fill the entire request. Extra candidates
                # allow deduplication/authorization checks before the final cut.
                per_type_k = requested_k * 2
                retrieved_docs = []
                for source_type in active_types:
                    type_clauses = []
                    field = field_map[source_type]
                    for source_id in authorized_source_ids.get(source_type, []):
                        type_clauses.extend([
                            {field: str(source_id)},
                            {"source_id": str(source_id)},
                        ])
                    try:
                        retrieved_docs.extend(self.retriever.retrieve(
                            question,
                            top_k=per_type_k,
                            filter_dict={"$or": type_clauses},
                        ) or [])
                    except Exception:
                        retrieval_errors.append(source_type)
                        logger.exception("Retrieval failed for source type %s", source_type)
            else:
                filter_dict = {"$or": clauses}
                retrieved_docs = self.retriever.retrieve(
                    question,
                    top_k=requested_k,
                    filter_dict=filter_dict,
                )
        else:
            retrieved_docs = self.retriever.retrieve(
                question,
                top_k=requested_k,
            )

        # The legacy collection also contains document records that predate
        # per-user metadata. YouTube records always carry an owner, so filter
        # them here before they can enter another user's RAG context.
        user_id = metadata.get("user_id")
        is_youtube_question = any(
            term in question.lower() for term in _YOUTUBE_QUERY_TERMS
        )

        # A generic phrase such as "summarize the uploaded video" should not
        # lose the video's transcript to unrelated documents in the shared
        # collection. Search the same collection again, scoped to this user's
        # YouTube chunks, and merge the results without changing document or
        # website retrieval.
        if user_id and is_youtube_question and authorized_source_ids is None:
            try:
                youtube_docs = self.retriever.retrieve(
                    question,
                    top_k=requested_k,
                    filter_dict={
                        "$and": [
                            {"source_type": "youtube"},
                            {"user_id": user_id},
                        ]
                    },
                )
            except Exception:
                retrieval_errors.append("youtube")
                logger.exception("Supplemental YouTube retrieval failed")
                youtube_docs = []
            retrieved_docs = (youtube_docs or []) + retrieved_docs

        if user_id:
            retrieved_docs = [
                doc
                for doc in retrieved_docs
                if (
                    doc[2].get("source_type") != "youtube"
                    or doc[2].get("user_id") == user_id
                )
            ]

        # A vector index can retain chunks after a source is deleted, and older
        # chunks may not contain owner metadata. When a chat request supplies
        # the database-authorized source IDs, reject every result that cannot be
        # tied to one of those live, owned sources. This is intentionally a
        # post-retrieval check as a defense-in-depth boundary for legacy Chroma
        # records as well as newly indexed ones.
        if authorized_source_ids is not None:
            retrieved_docs = [
                doc
                for doc in retrieved_docs
                if self._is_authorized_source(doc[2], authorized_source_ids)
            ]

        # Chroma returns distances, so lower scores win across modalities.
        # Deduplicate and discard empty chunks before consuming the final quota.
        unique_docs = []
        seen = set()
        for doc in sorted(retrieved_docs, key=lambda item: float(item[1])):
            if (
                not isinstance(doc[0], str)
                or not doc[0].strip()
                or not math.isfinite(float(doc[1]))
            ):
                continue
            key = PromptBuilder.chunk_id(doc[0], doc[2])
            if key not in seen:
                seen.add(key)
                unique_docs.append(doc)
        retrieved_docs = unique_docs[:requested_k]

        logger.info(
            "[RAG DEBUG] chunks_before_context=%d; chunk_content_lengths=%s; "
            "source_ids=%s",
            len(retrieved_docs),
            [len(doc[0]) if isinstance(doc[0], str) else 0 for doc in retrieved_docs],
            sorted(
                {
                    str(
                        doc[2].get("source_id")
                        or doc[2].get("document_id")
                        or doc[2].get("website_id")
                        or doc[2].get("youtube_source_id")
                    )
                    for doc in retrieved_docs
                    if (
                        doc[2].get("source_id")
                        or doc[2].get("document_id")
                        or doc[2].get("website_id")
                        or doc[2].get("youtube_source_id")
                    )
                }
            ),
        )

        source_types = [
            doc[2].get(
                "source_type",
                "website" if doc[2].get("website_id") else "document",
            )
            for doc in retrieved_docs
        ]
        source_ids = [
            doc[2].get("source_id")
            or doc[2].get("document_id")
            or doc[2].get("website_id")
            or doc[2].get("youtube_source_id")
            for doc in retrieved_docs
        ]
        youtube_source_ids = [
            doc[2].get("youtube_source_id")
            for doc in retrieved_docs
            if doc[2].get("source_type") == "youtube"
        ]
        logger.info(
            "[RAG] Retrieved chunk count: %d; YouTube: %d; Document: %d; "
            "Website: %d; source types=%s; source IDs=%s; YouTube source IDs=%s",
            len(retrieved_docs),
            source_types.count("youtube"),
            source_types.count("document"),
            source_types.count("website"),
            sorted(set(source_types)),
            sorted({str(source_id) for source_id in source_ids if source_id}),
            sorted({str(source_id) for source_id in youtube_source_ids if source_id}),
        )

        best_score = min((doc[1] for doc in retrieved_docs), default=None)

        # A Chroma distance is collection/model dependent.  It is useful for
        # observability, but must not silently discard retrieved transcript
        # chunks between retrieval and prompt construction.
        if best_score is not None and best_score > relevance_threshold:
            logger.info(
                "[RAG] Best retrieval distance %.4f exceeds advisory threshold "
                "%.2f; retaining retrieved context",
                best_score,
                relevance_threshold,
            )

        logger.info(
            "[RAG DEBUG] chunks_after_context_filter=%d",
            len(retrieved_docs),
        )

        retrieval_metadata = self._retrieval_metadata(retrieved_docs)
        return {
            **state,
            "retrieved_docs": retrieved_docs,
            "metadata": {
                **state.get("metadata", {}),
                "num_retrieved": len(retrieved_docs),
                "best_retrieval_distance": best_score,
                "rag_context_used": bool(retrieved_docs),
                "retrieval": retrieval_metadata,
                "retrieval_errors": retrieval_errors,
            },
        }

    @staticmethod
    def _source_type_and_id(metadata: Dict[str, Any]) -> tuple[str, str | None]:
        """Normalize source identity from current and legacy index metadata."""
        source_type = metadata.get("source_type")
        if source_type == "youtube" or metadata.get("youtube_source_id"):
            source_id = metadata.get("youtube_source_id") or metadata.get("source_id")
            return "youtube", str(source_id) if source_id else None
        if source_type == "website" or metadata.get("website_id"):
            source_id = metadata.get("website_id") or metadata.get("source_id")
            return "website", str(source_id) if source_id else None
        return "document", (
            str(metadata.get("document_id") or metadata.get("source_id"))
            if (metadata.get("document_id") or metadata.get("source_id"))
            else None
        )

    @classmethod
    def _is_authorized_source(
        cls, metadata: Dict[str, Any], authorized_source_ids: Dict[str, List[str]]
    ) -> bool:
        source_type, source_id = cls._source_type_and_id(metadata)
        return bool(source_id) and source_id in set(authorized_source_ids.get(source_type, []))

    @classmethod
    def _retrieval_metadata(cls, documents: List[tuple]) -> Dict[str, Any]:
        ids = {"document": set(), "website": set(), "youtube": set()}
        for _, _, metadata in documents:
            source_type, source_id = cls._source_type_and_id(metadata)
            if source_id:
                ids[source_type].add(source_id)
        return {
            "chunk_count": len(documents),
            "document_ids": sorted(ids["document"]),
            "website_ids": sorted(ids["website"]),
            "youtube_ids": sorted(ids["youtube"]),
        }

    @staticmethod
    def _origin_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Return stable, user-facing provenance fields for prompt/citations."""
        source_type, source_id = RAGPipeline._source_type_and_id(metadata)
        origin = {
            "source_type": source_type,
            "source_id": source_id,
            "source_name": (
                metadata.get("title")
                or metadata.get("filename")
                or metadata.get("name")
                or metadata.get("youtube_url")
                or metadata.get("url")
                or "Unknown source"
            ),
        }
        for key in ("title", "filename", "url", "youtube_url"):
            if metadata.get(key):
                origin[key] = metadata[key]
        return origin

    def _rerank_documents(self, state: RAGState) -> RAGState:
        """Rerank retrieved documents."""
        question = state["question"]
        retrieved_docs = state["retrieved_docs"]

        if self.reranker:
            reranked_docs = self.reranker.rerank(question, retrieved_docs)
        else:
            reranked_docs = retrieved_docs

        return {
            **state,
            "reranked_docs": reranked_docs,
            "metadata": {
                **state.get("metadata", {}),
                "num_reranked": len(reranked_docs),
            },
        }

    def _create_prompt(self, state: RAGState) -> RAGState:
        """Create the prompt from question and context."""
        question = state["question"]
        reranked_docs = state["reranked_docs"]

        # Convert reranked docs to expected format (remove rerank score)
        context_docs = [
            (doc[0], doc[1], {**doc[2], **self._origin_metadata(doc[2])})
            for doc in reranked_docs
        ]

        # Pack once so the model, diagnostics, and citations share one result.
        packed = self.prompt_builder.pack_context(context_docs)
        messages = self.prompt_builder.build_rag_messages(
            question=question,
            context_documents=context_docs,
            include_metadata=True,
            include_scores=False,
            packed_context=packed,
        )

        # Also build string prompt for logging
        prompt = self.prompt_builder.build_rag_prompt(
            question=question, context_documents=context_docs, packed_context=packed,
        )

        context_chunk_count = len(packed.documents)
        context_length = len(packed.text)
        context_sources = [
            {
                "source_type": doc[2].get("source_type", "document"),
                "source_id": doc[2].get("source_id")
                or doc[2].get("document_id")
                or doc[2].get("website_id")
                or doc[2].get("youtube_source_id"),
                "content_length": len(doc[0]),
            }
            for doc in packed.documents[:3]
        ]
        logger.info(
            "[RAG] Context length: %d characters across %d chunks",
            context_length,
            context_chunk_count,
        )
        logger.info(
            "[LLM] Context passed to LLM: %d characters; sources=%s",
            context_length,
            context_sources,
        )
        logger.info("[RAG DEBUG] final_context_length=%d", context_length)

        return {
            **state, "messages": messages, "prompt": prompt,
            "context_documents": packed.documents,
            "metadata": {
                **state.get("metadata", {}),
                "included_chunk_ids": packed.chunk_ids,
                "context_chunk_count": context_chunk_count,
                "context_length": context_length,
                "rag_context_used": bool(packed.documents),
            },
        }

    def _generate_response(self, state: RAGState) -> RAGState:
        """Generate response using LLM."""
        messages = state["messages"]

        # Convert to LangChain message format. History is bounded before it is
        # inserted so a long session cannot consume the entire model context.
        lc_messages: list[object] = []
        for index, msg in enumerate(messages):
            if msg["role"] == "system":
                from langchain_core.messages import SystemMessage

                lc_messages.append(SystemMessage(content=msg["content"]))
                history_chars = 0
                for historical in reversed(state.get("history", [])):
                    content = str(historical.get("content", ""))
                    if not content or history_chars + len(content) > 6000:
                        break
                    history_chars += len(content)
                history = list(state.get("history", []))
                if history_chars:
                    from langchain_core.messages import AIMessage, HumanMessage

                    selected: list[Dict[str, str]] = []
                    used = 0
                    for historical in reversed(history):
                        content = str(historical.get("content", ""))
                        if not content or used + len(content) > 6000:
                            break
                        selected.append(historical)
                        used += len(content)
                    for historical in reversed(selected):
                        role = historical.get("role")
                        if role in {"assistant", "ai"}:
                            lc_messages.append(AIMessage(content=historical["content"]))
                        else:
                            lc_messages.append(HumanMessage(content=historical["content"]))
            elif msg["role"] in {"user", "human"}:
                from langchain_core.messages import HumanMessage

                lc_messages.append(HumanMessage(content=msg["content"]))

        generation_kwargs: dict[str, object] = {}
        generation_metadata = state.get("metadata", {})
        if generation_metadata.get("temperature") is not None:
            generation_kwargs["temperature"] = generation_metadata["temperature"]
        if generation_metadata.get("max_tokens") is not None:
            generation_kwargs["max_tokens"] = generation_metadata["max_tokens"]

        # Generate response with request-level settings. In particular, 0.0 is
        # a valid temperature and must not be replaced by a default.
        response = self.llm.invoke(lc_messages, **generation_kwargs)
        response_text = response.content if isinstance(response.content, str) else str(response.content)

        return {
            **state,
            "response": response_text,
            "metadata": {
                **state.get("metadata", {}),
                "response_length": len(response_text),
            },
        }

    def query(self, question: str) -> dict[str, object]:
        """Run a query through the RAG pipeline.

        Args:
            question: User's question

        Returns:
            Dictionary with response and metadata
        """
        # Initialize state
        initial_state: RAGState = {
            "question": question,
            "embedding": None,
            "retrieved_docs": [],
            "reranked_docs": [],
            "prompt": "",
            "messages": [],
            "history": [],
            "response": "",
            "metadata": {},
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Return response and metadata
        return {
            "question": final_state["question"],
            "response": final_state["response"],
            "context_documents": final_state.get("context_documents", []),
            "metadata": final_state["metadata"],
        }

    def add_documents(
        self, documents: List[str], metadatas: Optional[List[Dict]] = None
    ):
        """Add documents to the vector store.

        Args:
            documents: List of document texts
            metadatas: Optional metadata for each document
        """
        return self.retriever.add_documents(documents, metadatas)

    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        collection_stats = self.retriever.get_collection_stats()
        return {
            "collection": collection_stats,
            "components": {
                "embedding_model": self.embedding_manager.model,
                "llm_model": self.llm.model_name,
                "rerank_model": self.reranker.model_name if self.reranker else "None",
            },
        }


if __name__ == "__main__":
    # Example usage
    print("Initializing RAG pipeline...")
    pipeline = RAGPipeline()

    # Add sample documents
    print("\nAdding documents to vector store...")
    documents = [
        "LangChain is a framework for developing applications powered by language models. It provides abstractions for working with LLMs, chains, and agents.",
        "RAG (Retrieval Augmented Generation) combines information retrieval with text generation. It retrieves relevant documents and uses them as context for generating responses.",
        "Vector databases like ChromaDB and Pinecone store embeddings and enable efficient similarity search for semantic retrieval tasks.",
        "LangGraph extends LangChain with graph-based workflows. It allows building complex multi-step applications with state management and conditional logic.",
        "Reranking improves retrieval quality by using cross-encoder models to re-score documents based on their relevance to the query.",
        "Embeddings are dense vector representations of text that capture semantic meaning. They enable similarity-based search and retrieval.",
    ]

    metadatas = [
        {"source": "langchain_docs", "topic": "framework"},
        {"source": "rag_guide", "topic": "rag"},
        {"source": "vector_db_intro", "topic": "storage"},
        {"source": "langgraph_docs", "topic": "framework"},
        {"source": "reranking_paper", "topic": "retrieval"},
        {"source": "embedding_guide", "topic": "embedding"},
    ]

    pipeline.add_documents(documents, metadatas)

    # Run queries
    print("\n" + "=" * 80)
    print("Testing RAG Pipeline")
    print("=" * 80)

    queries = [
        "What is RAG and how does it work?",
        "How does LangGraph extend LangChain?",
        "Why is reranking important?",
    ]

    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 80)

        result = pipeline.query(query)

        print(f"\nResponse:\n{result['response']}")
        print(f"\nMetadata: {result['metadata']}")
        print("\nTop context documents:")
        for i, doc in enumerate(result["context_documents"][:2], 1):
            print(f"{i}. [{doc[3]:.3f}] {doc[0][:100]}...")

    # Pipeline stats
    print("\n" + "=" * 80)
    stats = pipeline.get_stats()
    print("Pipeline Statistics:")
    print(f"  Collection: {stats['collection']}")
    print(f"  Components: {stats['components']}")
