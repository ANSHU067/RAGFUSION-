"""Simple test runner for vector store without external dependencies."""

import sys
import traceback
from typing import Callable

import numpy as np

# Import directly from the module
sys.path.insert(0, '/sessions/wizardly-compassionate-goodall/mnt/RAGFUSION/backend/app/db')

# Import the vector store module directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "vector_store",
    "/sessions/wizardly-compassionate-goodall/mnt/RAGFUSION/backend/app/db/vector_store.py"
)
vector_store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vector_store)

VectorDocument = vector_store.VectorDocument
VectorStore = vector_store.VectorStore


class TestRunner:
    """Simple test runner."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def run_test(self, test_name: str, test_func: Callable):
        """Run a single test."""
        try:
            test_func()
            self.passed += 1
            print(f"✓ {test_name}")
        except AssertionError as e:
            self.failed += 1
            self.errors.append((test_name, str(e)))
            print(f"✗ {test_name}: {e}")
        except Exception as e:
            self.failed += 1
            self.errors.append((test_name, traceback.format_exc()))
            print(f"✗ {test_name}: {type(e).__name__}: {e}")

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print(f"Tests passed: {self.passed}")
        print(f"Tests failed: {self.failed}")
        print(f"Total tests: {self.passed + self.failed}")

        if self.failed > 0:
            print("\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}")

        return self.failed == 0


def create_sample_vectors():
    """Generate sample vectors."""
    np.random.seed(42)
    return [
        np.random.rand(384).astype(np.float32),
        np.random.rand(384).astype(np.float32),
        np.random.rand(384).astype(np.float32),
    ]


def create_sample_metadata():
    """Sample metadata."""
    return [
        {"source": "doc1", "category": "tech", "year": 2023},
        {"source": "doc2", "category": "science", "year": 2023},
        {"source": "doc3", "category": "tech", "year": 2024},
    ]


def test_insert():
    """Test insert operations."""
    print("\n--- INSERT TESTS ---")
    runner = TestRunner()

    def test_add_single_vector():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        vector_id = store.add_vector(vectors[0])
        assert vector_id is not None
        assert store.count() == 1

    def test_add_with_metadata():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        metadata = {"source": "test", "category": "demo"}
        vector_id = store.add_vector(vectors[0], metadata=metadata)
        doc = store.get_vector(vector_id)
        assert doc.metadata == metadata

    def test_add_with_custom_id():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        custom_id = "my-custom-id"
        vector_id = store.add_vector(vectors[0], id=custom_id)
        assert vector_id == custom_id

    def test_add_multiple_vectors():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        ids = store.add_vectors(vectors)
        assert len(ids) == 3
        assert store.count() == 3

    def test_add_wrong_dimension():
        store = VectorStore(dimension=384)
        wrong_vector = np.random.rand(128).astype(np.float32)
        try:
            store.add_vector(wrong_vector)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "dimension" in str(e).lower()

    def test_add_from_list():
        store = VectorStore(dimension=384)
        vector_list = [0.1] * 384
        vector_id = store.add_vector(vector_list)
        doc = store.get_vector(vector_id)
        assert isinstance(doc.vector, np.ndarray)

    runner.run_test("Add single vector", test_add_single_vector)
    runner.run_test("Add with metadata", test_add_with_metadata)
    runner.run_test("Add with custom ID", test_add_with_custom_id)
    runner.run_test("Add multiple vectors", test_add_multiple_vectors)
    runner.run_test("Add wrong dimension (error handling)", test_add_wrong_dimension)
    runner.run_test("Add from list", test_add_from_list)

    return runner


def test_delete():
    """Test delete operations."""
    print("\n--- DELETE TESTS ---")
    runner = TestRunner()

    def test_remove_existing():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        vector_id = store.add_vector(vectors[0])
        result = store.remove_vector(vector_id)
        assert result is True
        assert store.count() == 0

    def test_remove_nonexistent():
        store = VectorStore(dimension=384)
        result = store.remove_vector("nonexistent")
        assert result is False

    def test_remove_multiple():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        ids = store.add_vectors(vectors)
        count = store.remove_vectors(ids[:2])
        assert count == 2
        assert store.count() == 1

    def test_clear_all():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        store.add_vectors(vectors)
        store.clear()
        assert store.count() == 0

    runner.run_test("Remove existing vector", test_remove_existing)
    runner.run_test("Remove nonexistent vector", test_remove_nonexistent)
    runner.run_test("Remove multiple vectors", test_remove_multiple)
    runner.run_test("Clear all vectors", test_clear_all)

    return runner


def test_update():
    """Test update operations."""
    print("\n--- UPDATE TESTS ---")
    runner = TestRunner()

    def test_update_vector_only():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        vector_id = store.add_vector(vectors[0], metadata={"a": 1})
        result = store.update_vector(vector_id, vector=vectors[1])
        assert result is True
        doc = store.get_vector(vector_id)
        assert np.array_equal(doc.vector, vectors[1])

    def test_update_metadata_only():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        vector_id = store.add_vector(vectors[0], metadata={"a": 1})
        new_metadata = {"b": 2}
        result = store.update_vector(vector_id, metadata=new_metadata)
        assert result is True
        doc = store.get_vector(vector_id)
        assert doc.metadata == new_metadata

    def test_update_both():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        vector_id = store.add_vector(vectors[0], metadata={"a": 1})
        new_metadata = {"b": 2}
        result = store.update_vector(vector_id, vector=vectors[1], metadata=new_metadata)
        assert result is True
        doc = store.get_vector(vector_id)
        assert np.array_equal(doc.vector, vectors[1])
        assert doc.metadata == new_metadata

    def test_update_nonexistent():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        result = store.update_vector("nonexistent", vector=vectors[0])
        assert result is False

    runner.run_test("Update vector only", test_update_vector_only)
    runner.run_test("Update metadata only", test_update_metadata_only)
    runner.run_test("Update both vector and metadata", test_update_both)
    runner.run_test("Update nonexistent vector", test_update_nonexistent)

    return runner


def test_search():
    """Test search operations."""
    print("\n--- SEARCH TESTS ---")
    runner = TestRunner()

    def test_basic_search():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        ids = store.add_vectors(vectors)
        results = store.similarity_search(vectors[0], k=3)
        assert len(results) == 3
        # First result should be the vector itself
        assert results[0][0].id == ids[0]
        assert results[0][1] > 0.99

    def test_search_with_k():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        store.add_vectors(vectors)
        results = store.similarity_search(vectors[0], k=2)
        assert len(results) == 2

    def test_search_with_filter():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        metadata = create_sample_metadata()
        store.add_vectors(vectors, metadatas=metadata)
        results = store.similarity_search(vectors[0], k=5, filter={"category": "tech"})
        assert len(results) == 2
        for doc, _ in results:
            assert doc.metadata["category"] == "tech"

    def test_search_with_multiple_filters():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        metadata = create_sample_metadata()
        store.add_vectors(vectors, metadatas=metadata)
        results = store.similarity_search(
            vectors[0], k=5, filter={"category": "tech", "year": 2024}
        )
        assert len(results) == 1
        assert results[0][0].metadata["year"] == 2024

    def test_search_with_min_score():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        store.add_vectors(vectors)
        results = store.similarity_search(vectors[0], k=10, min_score=0.99)
        assert len(results) == 1

    def test_search_empty_store():
        store = VectorStore(dimension=384)
        vectors = create_sample_vectors()
        results = store.similarity_search(vectors[0], k=5)
        assert len(results) == 0

    def test_search_results_sorted():
        store = VectorStore(dimension=384)
        base_vector = np.ones(384, dtype=np.float32)
        similar_vector = base_vector + 0.1
        dissimilar_vector = -base_vector
        store.add_vectors([base_vector, similar_vector, dissimilar_vector])
        results = store.similarity_search(base_vector, k=3)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)

    runner.run_test("Basic similarity search", test_basic_search)
    runner.run_test("Search with k limit", test_search_with_k)
    runner.run_test("Search with metadata filter", test_search_with_filter)
    runner.run_test("Search with multiple filters", test_search_with_multiple_filters)
    runner.run_test("Search with min score", test_search_with_min_score)
    runner.run_test("Search empty store", test_search_empty_store)
    runner.run_test("Search results sorted by score", test_search_results_sorted)

    return runner


def main():
    """Run all tests."""
    print("=" * 70)
    print("VECTOR STORE TEST SUITE")
    print("=" * 70)

    runners = []
    runners.append(test_insert())
    runners.append(test_delete())
    runners.append(test_update())
    runners.append(test_search())

    # Overall summary
    total_passed = sum(r.passed for r in runners)
    total_failed = sum(r.failed for r in runners)

    print("\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)
    print(f"Total passed: {total_passed}")
    print(f"Total failed: {total_failed}")
    print(f"Total tests: {total_passed + total_failed}")

    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total_failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
