"""Example usage of the RAG pipeline.

This script demonstrates how to use the RAG pipeline with different configurations.
"""
from rag_pipeline import RAGPipeline
from retrieval import RetrieverManager
from reranking import HybridReranker, RerankerManager
from prompt_creation import PromptBuilder, PromptTemplates
import json


def example_basic_usage():
    """Basic RAG pipeline usage."""
    print("="*80)
    print("Example 1: Basic RAG Pipeline Usage")
    print("="*80)

    # Initialize pipeline
    pipeline = RAGPipeline(collection_name="example_basic")

    # Add documents
    documents = [
        "LangChain is a framework for developing applications powered by language models. "
        "It provides tools for prompt management, chains, agents, and memory.",

        "RAG (Retrieval Augmented Generation) is a technique that combines information retrieval "
        "with text generation. It retrieves relevant documents and uses them as context for LLM responses.",

        "Vector databases store embeddings and enable efficient similarity search. "
        "Popular options include ChromaDB, Pinecone, and Weaviate.",

        "LangGraph extends LangChain with graph-based workflows for building complex multi-agent systems. "
        "It provides state management and conditional logic for sophisticated applications.",

        "Embeddings are dense vector representations that capture semantic meaning. "
        "They enable similarity-based search and are fundamental to RAG systems.",
    ]

    metadatas = [
        {"source": "langchain_docs.md", "topic": "framework"},
        {"source": "rag_guide.md", "topic": "rag"},
        {"source": "vector_db_intro.md", "topic": "storage"},
        {"source": "langgraph_docs.md", "topic": "framework"},
        {"source": "embedding_guide.md", "topic": "embeddings"}
    ]

    print("\nAdding documents to vector store...")
    pipeline.add_documents(documents, metadatas)
    print(f"Added {len(documents)} documents")

    # Query the pipeline
    query = "What is RAG and how does it work?"
    print(f"\nQuery: {query}")
    print("-"*80)

    result = pipeline.query(query)

    print(f"\nResponse:\n{result['response']}")
    print(f"\nMetadata: {result['metadata']}")

    print("\nTop 3 context documents:")
    for i, (text, ret_score, meta, rerank_score) in enumerate(result['context_documents'][:3], 1):
        print(f"\n{i}. [Rerank: {rerank_score:.3f}] {meta.get('source', 'unknown')}")
        print(f"   {text[:150]}...")

    # Cleanup
    pipeline.retriever.delete_collection()
    print("\n✓ Example 1 complete\n")


def example_custom_prompts():
    """Using custom prompts with the RAG pipeline."""
    print("="*80)
    print("Example 2: Custom Prompt Templates")
    print("="*80)

    pipeline = RAGPipeline(collection_name="example_prompts")

    # Add documents
    documents = [
        "The Python programming language was created by Guido van Rossum in 1991.",
        "JavaScript was developed by Brendan Eich in 1995 for Netscape Navigator.",
        "Rust is a systems programming language focused on safety and performance.",
    ]

    pipeline.add_documents(documents)

    # Use custom prompt builder
    custom_builder = PromptBuilder(
        system_prompt="""You are a programming language expert. Answer questions concisely
with specific facts and dates when available."""
    )

    # Get retrieval results
    query = "When was Python created?"
    print(f"\nQuery: {query}")

    retrieval_results = pipeline.retriever.retrieve(query, top_k=3)
    reranked = pipeline.reranker.rerank(query, retrieval_results)
    context_docs = [(doc[0], doc[1], doc[2]) for doc in reranked]

    # Build custom prompt
    messages = custom_builder.build_rag_messages(
        question=query,
        context_documents=context_docs,
        include_scores=False
    )

    print("\nCustom prompt structure:")
    for msg in messages:
        print(f"\n{msg['role'].upper()}:")
        print(f"{msg['content'][:200]}...")

    # Use the standard pipeline query for actual response
    result = pipeline.query(query)
    print(f"\nResponse: {result['response']}")

    pipeline.retriever.delete_collection()
    print("\n✓ Example 2 complete\n")


def example_retrieval_only():
    """Using just the retrieval component."""
    print("="*80)
    print("Example 3: Retrieval-Only (No LLM)")
    print("="*80)

    # Initialize retriever
    retriever = RetrieverManager(collection_name="example_retrieval")

    documents = [
        "Machine learning is a subset of artificial intelligence.",
        "Deep learning uses neural networks with multiple layers.",
        "Natural language processing deals with text and speech.",
        "Computer vision enables machines to interpret visual information.",
    ]

    metadata = [
        {"topic": "ML", "difficulty": "beginner"},
        {"topic": "DL", "difficulty": "intermediate"},
        {"topic": "NLP", "difficulty": "beginner"},
        {"topic": "CV", "difficulty": "intermediate"}
    ]

    print("\nAdding documents...")
    retriever.add_documents(documents, metadata)

    # Retrieve with filters
    query = "What is deep learning?"
    print(f"\nQuery: {query}")

    results = retriever.retrieve(query, top_k=3)

    print("\nRetrieved documents:")
    for i, (text, score, meta) in enumerate(results, 1):
        print(f"\n{i}. Score: {score:.4f}")
        print(f"   Topic: {meta.get('topic')}, Difficulty: {meta.get('difficulty')}")
        print(f"   Text: {text}")

    retriever.delete_collection()
    print("\n✓ Example 3 complete\n")


def example_hybrid_reranking():
    """Using hybrid reranking with custom weights."""
    print("="*80)
    print("Example 4: Hybrid Reranking")
    print("="*80)

    retriever = RetrieverManager(collection_name="example_hybrid")
    reranker = RerankerManager()
    hybrid = HybridReranker(
        reranker=reranker,
        retrieval_weight=0.4,  # 40% retrieval score
        rerank_weight=0.6      # 60% rerank score
    )

    documents = [
        "Python is great for data science and machine learning applications.",
        "JavaScript is the language of the web, used for frontend and backend.",
        "Java is widely used for enterprise applications and Android development.",
        "C++ offers high performance for systems programming and game development.",
    ]

    retriever.add_documents(documents)

    query = "What language should I use for data science?"
    print(f"\nQuery: {query}")

    # Get initial retrieval results
    results = retriever.retrieve(query, top_k=4)

    print("\nInitial retrieval ranking:")
    for i, (text, score, meta) in enumerate(results, 1):
        print(f"{i}. [{score:.4f}] {text[:60]}...")

    # Apply hybrid reranking
    hybrid_results = hybrid.hybrid_rerank(query, results, top_k=4)

    print("\nAfter hybrid reranking:")
    for i, (text, ret_score, meta, rerank_score, hybrid_score) in enumerate(hybrid_results, 1):
        print(f"{i}. [Hybrid: {hybrid_score:.4f}, Rerank: {rerank_score:.4f}, Ret: {ret_score:.4f}]")
        print(f"   {text[:60]}...")

    retriever.delete_collection()
    print("\n✓ Example 4 complete\n")


def example_conversation_history():
    """RAG with conversation history."""
    print("="*80)
    print("Example 5: Conversational RAG")
    print("="*80)

    pipeline = RAGPipeline(collection_name="example_conversation")
    prompt_builder = PromptBuilder()

    documents = [
        "Python was created by Guido van Rossum and released in 1991.",
        "Python is known for its simple, readable syntax and extensive library ecosystem.",
        "Popular Python frameworks include Django, Flask, FastAPI, and PyTorch.",
    ]

    pipeline.add_documents(documents)

    # Simulated conversation
    conversation_history = [
        {"role": "user", "content": "Who created Python?"},
        {"role": "assistant", "content": "Python was created by Guido van Rossum."},
    ]

    # New question building on history
    new_query = "When was it released?"
    print(f"Conversation history:")
    for msg in conversation_history:
        print(f"  {msg['role']}: {msg['content']}")

    print(f"\nNew query: {new_query}")

    # Retrieve context
    results = pipeline.retriever.retrieve(new_query, top_k=3)
    reranked = pipeline.reranker.rerank(new_query, results)
    context_docs = [(doc[0], doc[1], doc[2]) for doc in reranked]

    # Build conversational prompt
    messages = prompt_builder.build_conversational_prompt(
        question=new_query,
        context_documents=context_docs,
        conversation_history=conversation_history,
        max_history=5
    )

    print("\nBuilt conversational prompt with context and history")
    print(f"Total messages: {len(messages)}")

    pipeline.retriever.delete_collection()
    print("\n✓ Example 5 complete\n")


def example_batch_queries():
    """Processing multiple queries efficiently."""
    print("="*80)
    print("Example 6: Batch Query Processing")
    print("="*80)

    pipeline = RAGPipeline(collection_name="example_batch")

    documents = [
        "The Eiffel Tower is located in Paris, France and was completed in 1889.",
        "The Great Wall of China was built over many centuries to protect against invasions.",
        "The Taj Mahal in India was built by Emperor Shah Jahan as a mausoleum for his wife.",
        "The Colosseum in Rome is an ancient amphitheater built in 70-80 AD.",
    ]

    pipeline.add_documents(documents)

    queries = [
        "Where is the Eiffel Tower?",
        "When was the Colosseum built?",
        "Who built the Taj Mahal?"
    ]

    results = []

    print("\nProcessing multiple queries...")
    for query in queries:
        result = pipeline.query(query)
        results.append({
            "query": query,
            "response": result["response"],
            "num_docs_used": result["metadata"].get("num_reranked", 0)
        })

        print(f"\nQ: {query}")
        print(f"A: {result['response'][:150]}...")

    # Summary
    print("\n" + "-"*80)
    print("Batch processing summary:")
    print(f"  Queries processed: {len(queries)}")
    print(f"  Average docs used: {sum(r['num_docs_used'] for r in results) / len(results):.1f}")

    pipeline.retriever.delete_collection()
    print("\n✓ Example 6 complete\n")


def main():
    """Run all examples."""
    print("\n")
    print("*"*80)
    print(" RAG PIPELINE EXAMPLES")
    print("*"*80)
    print("\n")

    try:
        example_basic_usage()
        example_custom_prompts()
        example_retrieval_only()
        example_hybrid_reranking()
        example_conversation_history()
        example_batch_queries()

        print("="*80)
        print("✓ All examples completed successfully!")
        print("="*80)
        print("\nNext steps:")
        print("  1. Run tests: pytest tests/ -v")
        print("  2. Check out config.py to customize settings")
        print("  3. Review individual modules for more advanced usage")
        print("\n")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
