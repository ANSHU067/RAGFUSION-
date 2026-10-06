"""Comprehensive tests for the vector store."""

import numpy as np
import pytest

from backend.app.db.vector_store import VectorDocument, VectorStore


@pytest.fixture
def vector_store():
    """Create a fresh vector store for testing."""
    return VectorStore(dimension=384)


@pytest.fixture
def sample_vectors():
    """Generate sample vectors for testing."""
    np.random.seed(42)
    return [
        np.random.rand(384).astype(np.float32),
        np.random.rand(384).astype(np.float32),
        np.random.rand(384).astype(np.float32),
    ]


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return [
        {"source": "doc1", "category": "tech", "year": 2023},
        {"source": "doc2", "category": "science", "year": 2023},
        {"source": "doc3", "category": "tech", "year": 2024},
    ]


class TestVectorStoreInsert:
    """Tests for inserting vectors."""

    def test_add_single_vector(self, vector_store, sample_vectors):
        """Test adding a single vector."""
        vector_id = vector_store.add_vector(sample_vectors[0])

        assert vector_id is not None
        assert vector_store.count() == 1
        assert vector_id in vector_store.list_ids()

    def test_add_vector_with_metadata(self, vector_store, sample_vectors, sample_metadata):
        """Test adding a vector with metadata."""
        vector_id = vector_store.add_vector(sample_vectors[0], metadata=sample_metadata[0])

        doc = vector_store.get_vector(vector_id)
        assert doc is not None
        assert doc.metadata == sample_metadata[0]

    def test_add_vector_with_custom_id(self, vector_store, sample_vectors):
        """Test adding a vector with a custom ID."""
        custom_id = "my-custom-id-123"
        vector_id = vector_store.add_vector(sample_vectors[0], id=custom_id)

        assert vector_id == custom_id
        assert vector_store.get_vector(custom_id) is not None

    def test_add_vector_wrong_dimension(self, vector_store):
        """Test that adding a vector with wrong dimension raises error."""
        wrong_dim_vector = np.random.rand(128).astype(np.float32)

        with pytest.raises(ValueError, match="dimension"):
            vector_store.add_vector(wrong_dim_vector)

    def test_add_vector_from_list(self, vector_store):
        """Test adding a vector from a Python list."""
        vector_list = [0.1] * 384
        vector_id = vector_store.add_vector(vector_list)

        assert vector_id is not None
        doc = vector_store.get_vector(vector_id)
        assert isinstance(doc.vector, np.ndarray)
        assert doc.vector.shape == (384,)

    def test_add_multiple_vectors(self, vector_store, sample_vectors, sample_metadata):
        """Test adding multiple vectors at once."""
        ids = vector_store.add_vectors(sample_vectors, metadatas=sample_metadata)

        assert len(ids) == 3
        assert vector_store.count() == 3
        for id in ids:
            assert vector_store.get_vector(id) is not None

    def test_add_multiple_vectors_with_custom_ids(self, vector_store, sample_vectors):
        """Test adding multiple vectors with custom IDs."""
        custom_ids = ["id1", "id2", "id3"]
        ids = vector_store.add_vectors(sample_vectors, ids=custom_ids)

        assert ids == custom_ids
        assert vector_store.count() == 3

    def test_add_multiple_vectors_length_mismatch(self, vector_store, sample_vectors):
        """Test that mismatched lengths raise an error."""
        with pytest.raises(ValueError, match="same length"):
            vector_store.add_vectors(sample_vectors, metadatas=[{"a": 1}])

    def test_add_empty_metadata(self, vector_store, sample_vectors):
        """Test adding a vector with empty metadata."""
        vector_id = vector_store.add_vector(sample_vectors[0], metadata={})

        doc = vector_store.get_vector(vector_id)
        assert doc.metadata == {}


class TestVectorStoreDelete:
    """Tests for deleting vectors."""

    def test_remove_existing_vector(self, vector_store, sample_vectors):
        """Test removing an existing vector."""
        vector_id = vector_store.add_vector(sample_vectors[0])
        assert vector_store.count() == 1

        result = vector_store.remove_vector(vector_id)

        assert result is True
        assert vector_store.count() == 0
        assert vector_store.get_vector(vector_id) is None

    def test_remove_nonexistent_vector(self, vector_store):
        """Test removing a vector that doesn't exist."""
        result = vector_store.remove_vector("nonexistent-id")
        assert result is False

    def test_remove_multiple_vectors(self, vector_store, sample_vectors):
        """Test removing multiple vectors."""
        ids = vector_store.add_vectors(sample_vectors)
        assert vector_store.count() == 3

        count = vector_store.remove_vectors(ids[:2])

        assert count == 2
        assert vector_store.count() == 1
        assert vector_store.get_vector(ids[2]) is not None

    def test_remove_multiple_with_nonexistent(self, vector_store, sample_vectors):
        """Test removing multiple vectors including nonexistent ones."""
        ids = vector_store.add_vectors(sample_vectors)
        ids_to_remove = [ids[0], "nonexistent", ids[1]]

        count = vector_store.remove_vectors(ids_to_remove)

        assert count == 2
        assert vector_store.count() == 1

    def test_clear_all_vectors(self, vector_store, sample_vectors):
        """Test clearing all vectors."""
        vector_store.add_vectors(sample_vectors)
        assert vector_store.count() == 3

        vector_store.clear()

        assert vector_store.count() == 0
        assert vector_store.list_ids() == []


class TestVectorStoreUpdate:
    """Tests for updating vectors."""

    def test_update_vector_only(self, vector_store, sample_vectors):
        """Test updating just the vector."""
        vector_id = vector_store.add_vector(sample_vectors[0], metadata={"a": 1})
        original_metadata = vector_store.get_vector(vector_id).metadata

        result = vector_store.update_vector(vector_id, vector=sample_vectors[1])

        assert result is True
        doc = vector_store.get_vector(vector_id)
        assert np.array_equal(doc.vector, sample_vectors[1])
        assert doc.metadata == original_metadata

    def test_update_metadata_only(self, vector_store, sample_vectors):
        """Test updating just the metadata."""
        vector_id = vector_store.add_vector(sample_vectors[0], metadata={"a": 1})
        original_vector = vector_store.get_vector(vector_id).vector.copy()
        new_metadata = {"b": 2, "c": 3}

        result = vector_store.update_vector(vector_id, metadata=new_metadata)

        assert result is True
        doc = vector_store.get_vector(vector_id)
        assert np.array_equal(doc.vector, original_vector)
        assert doc.metadata == new_metadata

    def test_update_both_vector_and_metadata(self, vector_store, sample_vectors):
        """Test updating both vector and metadata."""
        vector_id = vector_store.add_vector(sample_vectors[0], metadata={"a": 1})
        new_metadata = {"b": 2}

        result = vector_store.update_vector(
            vector_id, vector=sample_vectors[1], metadata=new_metadata
        )

        assert result is True
        doc = vector_store.get_vector(vector_id)
        assert np.array_equal(doc.vector, sample_vectors[1])
        assert doc.metadata == new_metadata

    def test_update_nonexistent_vector(self, vector_store, sample_vectors):
        """Test updating a vector that doesn't exist."""
        result = vector_store.update_vector("nonexistent", vector=sample_vectors[0])
        assert result is False

    def test_update_with_wrong_dimension(self, vector_store, sample_vectors):
        """Test that updating with wrong dimension raises error."""
        vector_id = vector_store.add_vector(sample_vectors[0])
        wrong_dim_vector = np.random.rand(128).astype(np.float32)

        with pytest.raises(ValueError, match="dimension"):
            vector_store.update_vector(vector_id, vector=wrong_dim_vector)


class TestVectorStoreSearch:
    """Tests for similarity search."""

    def test_basic_similarity_search(self, vector_store, sample_vectors):
        """Test basic similarity search."""
        ids = vector_store.add_vectors(sample_vectors)

        # Search with the first vector itself
        results = vector_store.similarity_search(sample_vectors[0], k=3)

        assert len(results) == 3
        # First result should be the vector itself with similarity ~1.0
        assert results[0][0].id == ids[0]
        assert results[0][1] > 0.99

    def test_similarity_search_with_k(self, vector_store, sample_vectors):
        """Test limiting search results with k."""
        vector_store.add_vectors(sample_vectors)

        results = vector_store.similarity_search(sample_vectors[0], k=2)

        assert len(results) == 2

    def test_similarity_search_with_metadata_filter(self, vector_store, sample_vectors, sample_metadata):
        """Test search with metadata filtering."""
        vector_store.add_vectors(sample_vectors, metadatas=sample_metadata)

        # Filter for tech category only
        results = vector_store.similarity_search(
            sample_vectors[0], k=5, filter={"category": "tech"}
        )

        assert len(results) == 2
        for doc, _ in results:
            assert doc.metadata["category"] == "tech"

    def test_similarity_search_with_multiple_filters(self, vector_store, sample_vectors, sample_metadata):
        """Test search with multiple metadata filters."""
        vector_store.add_vectors(sample_vectors, metadatas=sample_metadata)

        # Filter for tech AND 2024
        results = vector_store.similarity_search(
            sample_vectors[0], k=5, filter={"category": "tech", "year": 2024}
        )

        assert len(results) == 1
        assert results[0][0].metadata["category"] == "tech"
        assert results[0][0].metadata["year"] == 2024

    def test_similarity_search_no_matches(self, vector_store, sample_vectors, sample_metadata):
        """Test search with filter that matches nothing."""
        vector_store.add_vectors(sample_vectors, metadatas=sample_metadata)

        results = vector_store.similarity_search(
            sample_vectors[0], k=5, filter={"category": "nonexistent"}
        )

        assert len(results) == 0

    def test_similarity_search_with_min_score(self, vector_store, sample_vectors):
        """Test search with minimum similarity threshold."""
        vector_store.add_vectors(sample_vectors)

        # Set a high minimum score
        results = vector_store.similarity_search(
            sample_vectors[0], k=10, min_score=0.99
        )

        # Should only return the vector itself
        assert len(results) == 1
        for _, score in results:
            assert score >= 0.99

    def test_similarity_search_empty_store(self, vector_store, sample_vectors):
        """Test search on empty store."""
        results = vector_store.similarity_search(sample_vectors[0], k=5)
        assert len(results) == 0

    def test_similarity_search_wrong_dimension(self, vector_store, sample_vectors):
        """Test that searching with wrong dimension raises error."""
        vector_store.add_vectors(sample_vectors)
        wrong_dim_vector = np.random.rand(128).astype(np.float32)

        with pytest.raises(ValueError, match="dimension"):
            vector_store.similarity_search(wrong_dim_vector, k=5)

    def test_similarity_scores_are_sorted(self, vector_store):
        """Test that similarity search results are sorted by score."""
        # Create vectors with known relationships
        base_vector = np.ones(384, dtype=np.float32)
        similar_vector = base_vector + 0.1
        dissimilar_vector = -base_vector

        vector_store.add_vectors([base_vector, similar_vector, dissimilar_vector])

        results = vector_store.similarity_search(base_vector, k=3)

        # Scores should be in descending order
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)


class TestVectorStoreUtilities:
    """Tests for utility methods."""

    def test_count_empty_store(self, vector_store):
        """Test count on empty store."""
        assert vector_store.count() == 0

    def test_count_with_vectors(self, vector_store, sample_vectors):
        """Test count with vectors."""
        vector_store.add_vectors(sample_vectors)
        assert vector_store.count() == 3

    def test_list_ids_empty_store(self, vector_store):
        """Test list_ids on empty store."""
        assert vector_store.list_ids() == []

    def test_list_ids_with_vectors(self, vector_store, sample_vectors):
        """Test list_ids with vectors."""
        ids = vector_store.add_vectors(sample_vectors)
        listed_ids = vector_store.list_ids()

        assert set(ids) == set(listed_ids)
        assert len(listed_ids) == 3

    def test_get_nonexistent_vector(self, vector_store):
        """Test getting a vector that doesn't exist."""
        doc = vector_store.get_vector("nonexistent")
        assert doc is None


class TestVectorDocument:
    """Tests for VectorDocument class."""

    def test_create_document_with_numpy_array(self):
        """Test creating a document with numpy array."""
        vector = np.random.rand(384).astype(np.float32)
        doc = VectorDocument(id="test", vector=vector, metadata={"a": 1})

        assert doc.id == "test"
        assert isinstance(doc.vector, np.ndarray)
        assert doc.vector.dtype == np.float32

    def test_create_document_with_list(self):
        """Test creating a document with a list."""
        vector_list = [0.1] * 384
        doc = VectorDocument(id="test", vector=vector_list)

        assert isinstance(doc.vector, np.ndarray)
        assert doc.vector.dtype == np.float32
        assert doc.vector.shape == (384,)

    def test_document_default_metadata(self):
        """Test that metadata defaults to empty dict."""
        vector = np.random.rand(384).astype(np.float32)
        doc = VectorDocument(id="test", vector=vector)

        assert doc.metadata == {}


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_zero_vectors(self, vector_store):
        """Test with zero vectors."""
        zero_vector = np.zeros(384, dtype=np.float32)
        vector_id = vector_store.add_vector(zero_vector)

        results = vector_store.similarity_search(zero_vector, k=1)
        assert len(results) == 1

    def test_large_k_value(self, vector_store, sample_vectors):
        """Test search with k larger than number of documents."""
        vector_store.add_vectors(sample_vectors)

        results = vector_store.similarity_search(sample_vectors[0], k=100)

        # Should return all 3 documents
        assert len(results) == 3

    def test_negative_values_in_vector(self, vector_store):
        """Test vectors with negative values."""
        vector_with_negatives = np.random.randn(384).astype(np.float32)
        vector_id = vector_store.add_vector(vector_with_negatives)

        assert vector_id is not None
        doc = vector_store.get_vector(vector_id)
        assert doc is not None

    def test_very_high_dimensional_space(self):
        """Test with high dimensional vectors."""
        high_dim_store = VectorStore(dimension=1536)
        vector = np.random.rand(1536).astype(np.float32)

        vector_id = high_dim_store.add_vector(vector)
        assert vector_id is not None

    def test_metadata_with_nested_structures(self, vector_store, sample_vectors):
        """Test metadata with nested dictionaries and lists."""
        complex_metadata = {
            "title": "Test Document",
            "tags": ["ai", "ml", "nlp"],
            "author": {
                "name": "John Doe",
                "email": "john@example.com"
            },
            "stats": {
                "views": 100,
                "likes": 50
            }
        }

        vector_id = vector_store.add_vector(sample_vectors[0], metadata=complex_metadata)
        doc = vector_store.get_vector(vector_id)

        assert doc.metadata == complex_metadata
        assert doc.metadata["tags"] == ["ai", "ml", "nlp"]
        assert doc.metadata["author"]["name"] == "John Doe"
