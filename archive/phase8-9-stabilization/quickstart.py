#!/usr/bin/env python3
"""
Quick Start Script for RAG Pipeline
Run this to verify installation and see the pipeline in action.
"""
import sys
import os

def check_environment():
    """Check if environment is properly set up."""
    print("🔍 Checking environment...")

    # Check for .env file
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("   Run: cp .env.example .env")
        print("   Then add your OPENAI_API_KEY")
        return False

    # Check for OpenAI API key
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        print("❌ OPENAI_API_KEY not set in .env")
        print("   Edit .env and add your OpenAI API key")
        return False

    print("✅ Environment configured")
    return True


def test_imports():
    """Test if all required modules can be imported."""
    print("\n📦 Testing imports...")

    try:
        from rag_pipeline import RAGPipeline
        from embedding import EmbeddingManager
        from retrieval import RetrieverManager
        from reranking import RerankerManager
        from prompt_creation import PromptBuilder
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Run: pip install -r requirements.txt")
        return False


def run_simple_demo():
    """Run a simple RAG pipeline demo."""
    print("\n🚀 Running simple RAG demo...")
    print("-" * 60)

    from rag_pipeline import RAGPipeline

    # Initialize pipeline
    print("\n1. Initializing pipeline...")
    pipeline = RAGPipeline(collection_name="quickstart_demo")

    # Add sample documents
    print("2. Adding sample documents...")
    documents = [
        "Python is a high-level programming language known for its simplicity and readability. Created by Guido van Rossum in 1991.",
        "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
        "Natural language processing (NLP) is a branch of AI that helps computers understand, interpret and manipulate human language.",
    ]

    metadatas = [
        {"topic": "programming", "source": "python_guide"},
        {"topic": "ai", "source": "ml_intro"},
        {"topic": "ai", "source": "nlp_basics"}
    ]

    pipeline.add_documents(documents, metadatas)
    print(f"   Added {len(documents)} documents")

    # Query the pipeline
    print("\n3. Querying the pipeline...")
    query = "What is machine learning?"
    print(f"   Query: '{query}'")

    result = pipeline.query(query)

    print("\n4. Results:")
    print(f"   Response: {result['response']}")
    print(f"\n   Retrieved {result['metadata']['num_retrieved']} documents")
    print(f"   Reranked to top {result['metadata']['num_reranked']}")

    print("\n   Top context document:")
    top_doc = result['context_documents'][0]
    print(f"   - Rerank score: {top_doc[3]:.3f}")
    print(f"   - Text: {top_doc[0][:100]}...")

    # Cleanup
    print("\n5. Cleaning up...")
    pipeline.retriever.delete_collection()

    print("\n" + "=" * 60)
    print("✅ Demo completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("  • Run full examples: python examples.py")
    print("  • Run tests: pytest tests/ -v")
    print("  • Read documentation: RAG_PIPELINE_README.md")


def main():
    """Main entry point."""
    print("=" * 60)
    print("  RAG Pipeline - Quick Start")
    print("=" * 60)

    # Check environment
    if not check_environment():
        print("\n❌ Environment setup incomplete")
        sys.exit(1)

    # Test imports
    if not test_imports():
        print("\n❌ Dependencies not installed")
        sys.exit(1)

    # Run demo
    try:
        run_simple_demo()
    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n✨ All checks passed! Your RAG pipeline is ready to use.\n")


if __name__ == "__main__":
    main()
