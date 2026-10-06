# RAG Pipeline

A comprehensive Retrieval-Augmented Generation (RAG) pipeline built with LangChain and LangGraph, featuring advanced retrieval, reranking, and testing capabilities.

## Features

- **Complete RAG Pipeline**: Question embedding → Retrieval → Reranking → Prompt creation → Response generation
- **LangGraph Orchestration**: State-managed workflow for complex multi-step processing
- **Vector Search**: ChromaDB-based semantic search with efficient similarity matching
- **Advanced Reranking**: Cross-encoder reranking with hybrid scoring options
- **Flexible Prompting**: Multiple prompt templates and customization options
- **Comprehensive Testing**: Retrieval accuracy, hallucination detection, and injection attack tests

## Architecture

```
Question
    ↓
Embedding (OpenAI)
    ↓
Retrieval (ChromaDB + Semantic Search)
    ↓
Reranking (Cross-Encoder)
    ↓
Prompt Creation (Context + Question)
    ↓
Response Generation (LLM)
```

## Installation

1. Clone the repository and navigate to the project directory:
```bash
cd RAGFUSION
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Quick Start

```python
from rag_pipeline import RAGPipeline

# Initialize pipeline
pipeline = RAGPipeline(collection_name="my_documents")

# Add documents
documents = [
    "LangChain is a framework for developing LLM applications.",
    "RAG combines retrieval with generation for better responses.",
]
pipeline.add_documents(documents)

# Query
result = pipeline.query("What is RAG?")
print(result['response'])
```

## Components

### 1. Embedding (`embedding.py`)
Handles document chunking and embedding generation using OpenAI's embedding models.

```python
from embedding import EmbeddingManager

embedding_manager = EmbeddingManager()
chunks, embeddings = embedding_manager.embed_and_chunk(documents)
```

### 2. Retrieval (`retrieval.py`)
Vector-based document retrieval using ChromaDB.

```python
from retrieval import RetrieverManager

retriever = RetrieverManager(collection_name="docs")
retriever.add_documents(documents, metadatas)
results = retriever.retrieve(query, top_k=5)
```

### 3. Reranking (`reranking.py`)
Improves retrieval quality using cross-encoder models.

```python
from reranking import RerankerManager, HybridReranker

reranker = RerankerManager()
reranked = reranker.rerank(query, retrieved_docs, top_k=3)

# Hybrid scoring (combines retrieval + reranking)
hybrid = HybridReranker(retrieval_weight=0.3, rerank_weight=0.7)
results = hybrid.hybrid_rerank(query, retrieved_docs)
```

### 4. Prompt Creation (`prompt_creation.py`)
Flexible prompt engineering and context formatting.

```python
from prompt_creation import PromptBuilder

builder = PromptBuilder()
messages = builder.build_rag_messages(
    question=query,
    context_documents=docs,
    include_metadata=True
)
```

### 5. RAG Pipeline (`rag_pipeline.py`)
Complete LangGraph-orchestrated pipeline.

```python
from rag_pipeline import RAGPipeline

pipeline = RAGPipeline(
    collection_name="my_docs",
    llm_model="gpt-4",
    temperature=0.0
)

result = pipeline.query("Your question here")
```

## Testing

The project includes comprehensive tests for retrieval accuracy, hallucination detection, and security.

### Run all tests:
```bash
pytest tests/ -v
```

### Run specific test suites:
```bash
# Retrieval accuracy tests
pytest tests/test_retrieval_accuracy.py -v -s

# Hallucination detection tests
pytest tests/test_hallucination.py -v -s

# Context injection security tests
pytest tests/test_context_injection.py -v -s
```

### Test Coverage

**Retrieval Accuracy** (`test_retrieval_accuracy.py`):
- Precision@K, Recall@K, F1@K
- Mean Reciprocal Rank (MRR)
- Average Precision (AP)
- Normalized Discounted Cumulative Gain (NDCG)

**Hallucination Detection** (`test_hallucination.py`):
- Factual consistency checking
- Proper refusal when information is missing
- Specific fact verification
- Contradiction detection

**Context Injection** (`test_context_injection.py`):
- Prompt injection resistance
- Delimiter confusion attacks
- Context isolation
- Special character handling
- Unicode and emoji support

## Examples

Run the examples to see the pipeline in action:

```bash
python examples.py
```

Examples include:
1. Basic RAG usage
2. Custom prompt templates
3. Retrieval-only (no LLM)
4. Hybrid reranking
5. Conversational RAG
6. Batch query processing

## Configuration

Edit `config.py` to customize:

- **Embedding Model**: Default is `text-embedding-3-small`
- **LLM Model**: Default is `gpt-4`
- **Retrieval Settings**: `TOP_K_RETRIEVAL`, `TOP_K_RERANK`
- **Chunking**: `CHUNK_SIZE`, `CHUNK_OVERLAP`
- **Vector Store**: `VECTOR_STORE_PATH`

## Project Structure

```
RAGFUSION/
├── config.py                      # Configuration settings
├── embedding.py                   # Embedding generation
├── retrieval.py                   # Document retrieval
├── reranking.py                   # Document reranking
├── prompt_creation.py             # Prompt engineering
├── rag_pipeline.py               # Complete pipeline
├── examples.py                    # Usage examples
├── requirements.txt               # Dependencies
├── .env.example                   # Environment template
├── tests/
│   ├── test_retrieval_accuracy.py # Retrieval metrics
│   ├── test_hallucination.py      # Hallucination tests
│   └── test_context_injection.py  # Security tests
└── RAG_PIPELINE_README.md         # This file
```

## Advanced Usage

### Custom System Prompts

```python
from prompt_creation import PromptBuilder

custom_prompt = """You are an expert assistant specializing in technical documentation.
Always cite sources and be precise with technical terms."""

builder = PromptBuilder(system_prompt=custom_prompt)
```

### Metadata Filtering

```python
# Add documents with metadata
retriever.add_documents(
    documents=docs,
    metadatas=[{"topic": "python", "level": "advanced"}]
)

# Retrieve with filters
results = retriever.retrieve(
    query="Python features",
    filter_dict={"level": "advanced"}
)
```

### Conversational RAG

```python
# Build context-aware conversational prompts
messages = builder.build_conversational_prompt(
    question=current_question,
    context_documents=retrieved_docs,
    conversation_history=previous_messages,
    max_history=5
)
```

## Metrics & Evaluation

The pipeline includes built-in metrics for evaluation:

```python
from tests.test_retrieval_accuracy import RetrievalMetrics

# Calculate retrieval quality
precision = RetrievalMetrics.precision_at_k(retrieved_ids, relevant_ids, k=5)
mrr = RetrievalMetrics.mean_reciprocal_rank(retrieved_ids, relevant_ids)
ndcg = RetrievalMetrics.ndcg_at_k(retrieved_ids, relevance_scores, k=5)
```

## Performance Tips

1. **Batch Processing**: Process multiple documents at once for better efficiency
2. **Chunking Strategy**: Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` based on your documents
3. **Reranking**: Use hybrid reranking for best quality, or skip for faster responses
4. **Caching**: Vector embeddings are persisted in ChromaDB for reuse

## Troubleshooting

**Import Errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`

**API Key Issues**: Verify your OpenAI API key is set in `.env`

**Vector Store Errors**: Check that `VECTOR_STORE_PATH` directory exists and is writable

**Memory Issues**: Reduce `CHUNK_SIZE` or limit the number of documents for large datasets

## Contributing

Contributions are welcome! Please ensure:
- All tests pass before submitting
- New features include appropriate tests
- Code follows the existing style conventions

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [LangChain](https://github.com/langchain-ai/langchain) - LLM framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Graph-based workflows
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Sentence Transformers](https://www.sbert.net/) - Cross-encoder models
- [OpenAI](https://openai.com/) - Embeddings and LLM
