"""Prompt builder for RAG applications.

This module handles prompt engineering and context formatting for RAG pipelines.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
import json

from app.core.rag_config import get_rag_config


@dataclass(frozen=True)
class PackedContext:
    """The exact context and chunk identities accepted for one request."""

    text: str
    documents: List[Tuple[str, float, Dict]]

    @property
    def chunk_ids(self) -> List[str]:
        return [document[2]["chunk_id"] for document in self.documents]


class PromptBuilder:
    """Builds prompts for RAG applications."""

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        max_context_length: Optional[int] = None,
    ):
        """Initialize the prompt builder.

        Args:
            system_prompt: Default system prompt
            max_context_length: Maximum context length in characters
        """
        rag_config = get_rag_config()

        self.max_context_length = rag_config.max_context_length if max_context_length is None else max_context_length
        self.system_prompt = system_prompt or self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        """Get default hybrid system prompt."""
        return """
You are RagFusion AI, a friendly, intelligent, and conversational AI assistant.

Your responsibilities:

1. If relevant document context is provided, use it as your primary source.

2. If the document only partially answers the question, combine the document information with your own general knowledge.

3. If no useful document context is available, answer naturally using your own knowledge.

4. Never reply with:
   - "The context does not contain..."
   - "I can only answer from the provided context."

5. Instead:
   - Mention when information comes from the uploaded document.
   - Mention when information comes from your own knowledge if necessary.

6. Never contradict the uploaded document.

7. Be conversational, helpful, and professional.

8. If the user asks general questions, programming questions, reasoning questions, creative writing tasks, greetings, or casual conversation, respond naturally as an intelligent AI assistant.

9. When document context exists, prefer it, but do not ignore your own knowledge if it improves the answer.

10. Keep answers clear, accurate, and well structured.

11. If retrieved document context is irrelevant to the user's question, ignore it and answer using your own knowledge instead.
"""

    @staticmethod
    def _format_origin(metadata: Dict[str, Any]) -> str:
        """Format only canonical provenance fields for the model."""
        source_type = metadata.get("source_type")
        if source_type not in {"document", "website", "youtube"}:
            source_type = (
                "youtube" if metadata.get("youtube_source_id")
                else "website" if metadata.get("website_id")
                else "document"
            )
        source_id = metadata.get("source_id")
        source_name = (
            metadata.get("source_name")
            or metadata.get("title")
            or metadata.get("filename")
            or metadata.get("name")
            or "Unknown source"
        )
        parts = [f"type={source_type}", f"name={source_name}"]
        if source_id:
            parts.append(f"id={source_id}")
        url = metadata.get("url") or metadata.get("youtube_url")
        if url:
            parts.append(f"url={url}")
        filename = metadata.get("filename")
        if filename and filename != source_name:
            parts.append(f"filename={filename}")
        return ", ".join(parts)

    @staticmethod
    def chunk_id(text: str, metadata: Dict[str, Any]) -> str:
        """Retain explicit IDs, or derive a stable ID for legacy vector records."""
        if metadata.get("chunk_id") is not None:
            return str(metadata["chunk_id"])
        identity = {key: metadata.get(key) for key in (
            "source_type", "source_id", "document_id", "website_id",
            "youtube_source_id", "chunk_index", "chunk_idx",
        )}
        identity["text"] = text
        return hashlib.sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()

    def pack_context(
        self,
        context_documents: List[Tuple[str, float, Dict]],
        include_metadata: bool = True,
        include_scores: bool = False,
    ) -> PackedContext:
        """Pack whole chunks once; oversized chunks do not hide later small ones."""
        sections = []
        included = []
        current_length = 0
        for text, score, metadata in context_documents:
            if not text.strip():
                continue
            header_parts = [f"Document {len(included) + 1}"]
            if include_scores:
                header_parts.append(f"(Relevance: {score:.2f})")
            if include_metadata and metadata:
                header_parts.append(f"[Origin: {self._format_origin(metadata)}]")
            section = f"\n{' '.join(header_parts)}:\n{text}\n"
            if current_length + len(section) > self.max_context_length:
                continue
            sections.append(section)
            current_length += len(section)
            included.append((text, score, {**metadata, "chunk_id": self.chunk_id(text, metadata)}))
        return PackedContext(text="".join(sections), documents=included)

    @staticmethod
    def _no_context_notice(context_documents, packed: PackedContext) -> str:
        if packed.documents:
            return ""
        if context_documents:
            return (
                "\nNo source chunks fit the current context budget. Do not claim "
                "to have consulted or cite any uploaded sources in this answer.\n"
            )
        return (
            "\nNo current, authorized source chunks were retrieved. If the user asks "
            "about an uploaded document or source, clearly state that there are "
            "currently no uploaded documents available to reference. Do not infer "
            "that a source exists from earlier conversation text.\n"
        )

    def build_rag_prompt(
        self,
        question: str,
        context_documents: List[Tuple[str, float, Dict]],
        include_metadata: bool = True,
        include_scores: bool = False,
        packed_context: Optional[PackedContext] = None,
    ) -> str:
        """Build a RAG prompt from question and context.

        Args:
            question: User's question
            context_documents: List of (text, score, metadata) tuples
            include_metadata: Whether to include document metadata
            include_scores: Whether to include relevance scores

        Returns:
            Formatted prompt string
        """

        packed = packed_context if packed_context is not None else self.pack_context(
            context_documents, include_metadata, include_scores,
        )
        context = packed.text
        no_source_notice = self._no_context_notice(context_documents, packed)

        # Build full prompt
        prompt = f"""Context:
{context}

Question: {question}

Answer using the document context whenever it is relevant.
{no_source_notice}

If the context only partially answers the question,
combine it with your own knowledge.

If no useful context exists,
answer naturally using your own knowledge.
"""

        return prompt

    def build_rag_messages(
        self,
        question: str,
        context_documents: List[Tuple[str, float, Dict]],
        include_metadata: bool = True,
        include_scores: bool = False,
        system_prompt: Optional[str] = None,
        packed_context: Optional[PackedContext] = None,
    ) -> List[Dict[str, str]]:
        """Build messages for chat-based models.

        Args:
            question: User's question
            context_documents: List of (text, score, metadata) tuples
            include_metadata: Whether to include document metadata
            include_scores: Whether to include relevance scores
            system_prompt: Override system prompt

        Returns:
            List of message dictionaries
        """
        packed = packed_context if packed_context is not None else self.pack_context(
            context_documents, include_metadata, include_scores,
        )
        context = packed.text
        no_source_notice = self._no_context_notice(context_documents, packed)

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt or self.system_prompt},
            {
                "role": "user",
                "content": f"""
Document Context:
{context}

User Question:
{question}

Use the document whenever it is relevant.
{no_source_notice}

If it is insufficient,
supplement the answer with your own knowledge.

Do not refuse to answer merely because the document lacks information.
""",
            },
        ]

        return messages

    def build_conversational_prompt(
        self,
        question: str,
        context_documents: List[Tuple[str, float, Dict]],
        conversation_history: List[Dict[str, str]],
        max_history: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Build prompt with conversation history.

        Args:
            question: Current question
            context_documents: Retrieved context
            conversation_history: Previous messages
            max_history: Maximum number of history messages to include

        Returns:
            List of message dictionaries
        """
        rag_config = get_rag_config()
        max_hist = max_history or rag_config.max_conversation_history

        # Build context
        context_parts = []
        current_length = 0

        for i, (text, score, metadata) in enumerate(context_documents, 1):
            doc_section = f"\nDocument {i}:\n{text}\n"
            if current_length + len(doc_section) > self.max_context_length:
                break
            context_parts.append(doc_section)
            current_length += len(doc_section)

        context = "".join(context_parts)

        # Build messages with history
        messages = [
            {
                "role": "system",
                "content": self.system_prompt + f"""

Relevant Document Context:

{context}

Use the document whenever it helps.

Otherwise answer naturally using your own knowledge.
""",
            }
        ]

        # Add recent conversation history
        recent_history = (
            conversation_history[-max_hist:] if conversation_history else []
        )
        messages.extend(recent_history)

        # Add current question
        messages.append({"role": "user", "content": question})

        return messages

    def build_citation_prompt(
        self, question: str, context_documents: List[Tuple[str, float, Dict]]
    ) -> str:
        """Build prompt that encourages citation.

        Args:
            question: User's question
            context_documents: Retrieved context with metadata

        Returns:
            Formatted prompt with citation instructions
        """
        # Number documents for citation
        context_parts = []
        for i, (text, score, metadata) in enumerate(context_documents, 1):
            source = metadata.get("source", f"Source {i}")
            context_parts.append(f"[{i}] {source}:\n{text}\n")

        context = "\n".join(context_parts)

        prompt = f"""{self.system_prompt}

When answering, cite your sources using [1], [2], etc.

Context:
{context}

Question: {question}

Answer (with citations):"""

        return prompt


class PromptTemplates:
    """Collection of prompt templates for different use cases."""

    @staticmethod
    def qa_template() -> str:
        """Question answering template."""
        return """Answer the following question based on the context provided.

Context:
{context}

Question: {question}

Answer:"""

    @staticmethod
    def summarization_template() -> str:
        """Document summarization template."""
        return """Summarize the following documents concisely.

Documents:
{context}

Summary:"""

    @staticmethod
    def fact_checking_template() -> str:
        """Fact checking template."""
        return """Verify the following claim against the provided context.

Context:
{context}

Claim: {question}

Verification (state if the claim is supported, contradicted, or not mentioned):"""

    @staticmethod
    def comparison_template() -> str:
        """Comparison template."""
        return """Compare and contrast the information from multiple sources.

Sources:
{context}

Question: {question}

Comparison:"""


if __name__ == "__main__":
    # Example usage
    builder = PromptBuilder()

    question = "What is RAG and how does it work?"
    context_docs: list[tuple[str, float, dict[str, Any]]] = [
        (
            "RAG (Retrieval Augmented Generation) combines retrieval with generation. It retrieves relevant documents and uses them to generate informed responses.",
            0.92,
            {"source": "rag_overview.pdf", "page": 1},
        ),
        (
            "The RAG process involves: 1) embedding the query, 2) retrieving relevant documents, 3) reranking results, 4) generating a response using the context.",
            0.87,
            {"source": "rag_tutorial.md", "section": "Process"},
        ),
        (
            "Vector databases are commonly used in RAG systems to store and retrieve document embeddings efficiently.",
            0.75,
            {"source": "vector_db_guide.pdf", "page": 5},
        ),
    ]

    # Standard RAG prompt
    print("=== Standard RAG Prompt ===")
    prompt = builder.build_rag_prompt(question, context_docs, include_scores=True)
    print(prompt)

    # Chat messages format
    print("\n=== Chat Messages Format ===")
    messages = builder.build_rag_messages(question, context_docs, include_scores=True)
    for msg in messages:
        print(f"\n{msg['role'].upper()}:")
        print(msg["content"])

    # Citation prompt
    print("\n=== Citation Prompt ===")
    citation_prompt = builder.build_citation_prompt(question, context_docs)
    print(citation_prompt)
