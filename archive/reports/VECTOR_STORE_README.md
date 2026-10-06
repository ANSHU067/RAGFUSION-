# Vector Database Layer

A lightweight, in-memory vector database implementation with similarity search and metadata filtering capabilities.

## Features

### Core Operations
- **Add Vectors**: Insert single or multiple vectors with optional metadata and custom IDs
- **Remove Vectors**: Delete vectors by ID or clear the entire store
- **Update Vectors**: Modify existing vectors and/or their metadata
- **Similarity Search**: Find similar vectors using cosine similarity with optional metadata filtering

### Search Capabilities
- **k-NN Search**: Return top-k most similar vectors
- **Metadata Filtering**: Filter results by exact key-value matches (supports multiple filters)
- **Minimum Score Threshold**: Filter results by minimum similarity score
- **Sorted Results**: Results automatically sorted by similarity score (descending)

## Installation

The vector store only requires NumPy:

```bash
pip install numpy
```

## Usage

### Basic Example

```python
import numpy as np
from backend.app.db.vector_store import VectorStore

# Create a vector store (default dimension: 384)
store = VectorStore(dimension=384)

# Add a vector
vector = np.random.rand(384).astype(np.float32)
vector_id = store.add_vector(vector, metadata={"source": "doc1", "category": "tech"})

# Search for similar vectors
query = np.random.rand(384).astype(np.float32)
results = store.similarity_search(query, k=5)

for doc, similarity in results:
    print(f"ID: {doc.id}, Similarity: {similarity:.4f}, Metadata: {doc.metadata}")
```

### Adding Vectors

```python
# Single vector with metadata
vector_id = store.add_vector(
    vector=my_vector,
    metadata={"title": "Document 1", "year": 2023},
    id="custom-id-123"  # Optional custom ID
)

# Multiple vectors at once
vectors = [vector1, vector2, vector3]
metadatas = [
    {"source": "doc1"},
    {"source": "doc2"},
    {"source": "doc3"}
]
ids = store.add_vectors(vectors, metadatas=metadatas)
```

### Searching

```python
# Basic search
results = store.similarity_search(query_vector, k=10)

# Search with metadata filter
results = store.similarity_search(
    query_vector,
    k=10,
    filter={"category": "tech", "year": 2023}
)

# Search with minimum similarity threshold
results = store.similarity_search(
    query_vector,
    k=10,
    min_score=0.8
)
```

### Updating and Deleting

```python
# Update vector only
store.update_vector(vector_id, vector=new_vector)

# Update metadata only
store.update_vector(vector_id, metadata={"new_key": "value"})

# Update both
store.update_vector(vector_id, vector=new_vector, metadata=new_metadata)

# Delete a vector
store.remove_vector(vector_id)

# Delete multiple vectors
store.remove_vectors([id1, id2, id3])

# Clear all vectors
store.clear()
```

### Utility Methods

```python
# Get document by ID
doc = store.get_vector(vector_id)

# Count vectors
count = store.count()

# List all IDs
ids = store.list_ids()
```

## API Reference

### VectorStore

#### Constructor
```python
VectorStore(dimension: int = 384)
```
- `dimension`: Expected dimension of vectors

#### Methods

**add_vector**(vector, metadata=None, id=None) → str
- Adds a single vector to the store
- Returns the document ID

**add_vectors**(vectors, metadatas=None, ids=None) → list[str]
- Adds multiple vectors to the store
- Returns list of document IDs

**remove_vector**(id) → bool
- Removes a vector by ID
- Returns True if removed, False if not found

**remove_vectors**(ids) → int
- Removes multiple vectors
- Returns count of vectors actually removed

**update_vector**(id, vector=None, metadata=None) → bool
- Updates a vector and/or metadata
- Returns True if updated, False if not found

**get_vector**(id) → Optional[VectorDocument]
- Retrieves a document by ID
- Returns VectorDocument or None

**similarity_search**(query_vector, k=5, filter=None, min_score=0.0) → list[tuple[VectorDocument, float]]
- Searches for similar vectors
- Returns list of (document, score) tuples sorted by score

**clear**() → None
- Removes all documents from the store

**count**() → int
- Returns number of documents in the store

**list_ids**() → list[str]
- Returns all document IDs

### VectorDocument

A dataclass representing a document with vector embedding and metadata.

**Attributes:**
- `id`: str - Document identifier
- `vector`: np.ndarray - Embedding vector
- `metadata`: dict - Associated metadata

## Testing

Comprehensive tests are included covering:
- Insert operations (single, multiple, with metadata, custom IDs)
- Delete operations (single, multiple, clear)
- Update operations (vector, metadata, both)
- Search operations (basic, with filters, with thresholds)

Run tests:

```bash
# Simple standalone test
python test_vector_store_simple.py

# Pytest (if available)
pytest tests/test_vector_store.py -v
```

## Performance Characteristics

- **Storage**: In-memory dictionary, O(n) space complexity
- **Insert**: O(1) average case
- **Delete**: O(1) average case
- **Update**: O(1) average case
- **Search**: O(n*d) where n is number of documents and d is dimension
  - Linear scan with cosine similarity computation
  - Suitable for small to medium datasets (< 100k vectors)

## Limitations

- **In-memory only**: No persistence (store must be rebuilt on restart)
- **No indexing**: Uses brute-force search (no HNSW, IVF, or other approximate methods)
- **Single-threaded**: No concurrent access protection
- **Exact match filtering**: Metadata filters use exact equality only

## Future Enhancements

Potential improvements for production use:
- Persistence layer (save/load to disk)
- Approximate nearest neighbor search (HNSW, IVF)
- Thread-safe operations
- Advanced filtering (range queries, boolean logic)
- Batch operations optimization
- Distance metrics beyond cosine similarity
- Integration with vector databases (Pinecone, Weaviate, Qdrant)

## License

Part of the RAGFUSION project.
