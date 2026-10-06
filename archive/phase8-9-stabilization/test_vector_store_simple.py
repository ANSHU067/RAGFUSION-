"""Simple standalone test for vector store."""

import sys
import numpy as np

# Read and execute the vector store module
with open('/sessions/wizardly-compassionate-goodall/mnt/RAGFUSION/backend/app/db/vector_store.py', 'r') as f:
    code = f.read()
    exec(code, globals())


def test_insert():
    """Test insert operations."""
    print("\n=== INSERT TESTS ===")
    passed = 0
    failed = 0

    # Test 1: Add single vector
    try:
        store = VectorStore(dimension=384)
        vector = np.random.rand(384).astype(np.float32)
        vector_id = store.add_vector(vector)
        assert vector_id is not None
        assert store.count() == 1
        print("✓ Add single vector")
        passed += 1
    except Exception as e:
        print(f"✗ Add single vector: {e}")
        failed += 1

    # Test 2: Add with metadata
    try:
        store = VectorStore(dimension=384)
        vector = np.random.rand(384).astype(np.float32)
        metadata = {"source": "test", "category": "demo"}
        vector_id = store.add_vector(vector, metadata=metadata)
        doc = store.get_vector(vector_id)
        assert doc.metadata == metadata
        print("✓ Add with metadata")
        passed += 1
    except Exception as e:
        print(f"✗ Add with metadata: {e}")
        failed += 1

    # Test 3: Add with custom ID
    try:
        store = VectorStore(dimension=384)
        vector = np.random.rand(384).astype(np.float32)
        custom_id = "my-custom-id"
        vector_id = store.add_vector(vector, id=custom_id)
        assert vector_id == custom_id
        print("✓ Add with custom ID")
        passed += 1
    except Exception as e:
        print(f"✗ Add with custom ID: {e}")
        failed += 1

    # Test 4: Add multiple vectors
    try:
        store = VectorStore(dimension=384)
        vectors = [np.random.rand(384).astype(np.float32) for _ in range(3)]
        ids = store.add_vectors(vectors)
        assert len(ids) == 3
        assert store.count() == 3
        print("✓ Add multiple vectors")
        passed += 1
    except Exception as e:
        print(f"✗ Add multiple vectors: {e}")
        failed += 1

    # Test 5: Wrong dimension error
    try:
        store = VectorStore(dimension=384)
        wrong_vector = np.random.rand(128).astype(np.float32)
        try:
            store.add_vector(wrong_vector)
            print("✗ Wrong dimension error: Should have raised ValueError")
            failed += 1
        except ValueError:
            print("✓ Wrong dimension error")
            passed += 1
    except Exception as e:
        print(f"✗ Wrong dimension error: {e}")
        failed += 1

    # Test 6: Add from list
    try:
        store = VectorStore(dimension=384)
        vector_list = [0.1] * 384
        vector_id = store.add_vector(vector_list)
        doc = store.get_vector(vector_id)
        assert isinstance(doc.vector, np.ndarray)
        print("✓ Add from list")
        passed += 1
    except Exception as e:
        print(f"✗ Add from list: {e}")
        failed += 1

    return passed, failed


def test_delete():
    """Test delete operations."""
    print("\n=== DELETE TESTS ===")
    passed = 0
    failed = 0

    # Test 1: Remove existing vector
    try:
        store = VectorStore(dimension=384)
        vector = np.random.rand(384).astype(np.float32)
        vector_id = store.add_vector(vector)
        result = store.remove_vector(vector_id)
        assert result is True
        assert store.count() == 0
        print("✓ Remove existing vector")
        passed += 1
    except Exception as e:
        print(f"✗ Remove existing vector: {e}")
        failed += 1

    # Test 2: Remove nonexistent vector
    try:
        store = VectorStore(dimension=384)
        result = store.remove_vector("nonexistent")
        assert result is False
        print("✓ Remove nonexistent vector")
        passed += 1
    except Exception as e:
        print(f"✗ Remove nonexistent vector: {e}")
        failed += 1

    # Test 3: Remove multiple vectors
    try:
        store = VectorStore(dimension=384)
        vectors = [np.random.rand(384).astype(np.float32) for _ in range(3)]
        ids = store.add_vectors(vectors)
        count = store.remove_vectors(ids[:2])
        assert count == 2
        assert store.count() == 1
        print("✓ Remove multiple vectors")
        passed += 1
    except Exception as e:
        print(f"✗ Remove multiple vectors: {e}")
        failed += 1

    # Test 4: Clear all
    try:
        store = VectorStore(dimension=384)
        vectors = [np.random.rand(384).astype(np.float32) for _ in range(3)]
        store.add_vectors(vectors)
        store.clear()
        assert store.count() == 0
        print("✓ Clear all vectors")
        passed += 1
    except Exception as e:
        print(f"✗ Clear all vectors: {e}")
        failed += 1

    return passed, failed


def test_update():
    """Test update operations."""
    print("\n=== UPDATE TESTS ===")
    passed = 0
    failed = 0

    # Test 1: Update vector only
    try:
        store = VectorStore(dimension=384)
        v1 = np.random.rand(384).astype(np.float32)
        v2 = np.random.rand(384).astype(np.float32)
        vector_id = store.add_vector(v1, metadata={"a": 1})
        result = store.update_vector(vector_id, vector=v2)
        assert result is True
        doc = store.get_vector(vector_id)
        assert np.array_equal(doc.vector, v2)
        print("✓ Update vector only")
        passed += 1
    except Exception as e:
        print(f"✗ Update vector only: {e}")
        failed += 1

    # Test 2: Update metadata only
    try:
        store = VectorStore(dimension=384)
        vector = np.random.rand(384).astype(np.float32)
        vector_id = store.add_vector(vector, metadata={"a": 1})
        new_metadata = {"b": 2}
        result = store.update_vector(vector_id, metadata=new_metadata)
        assert result is True
        doc = store.get_vector(vector_id)
        assert doc.metadata == new_metadata
        print("✓ Update metadata only")
        passed += 1
    except Exception as e:
        print(f"✗ Update metadata only: {e}")
        failed += 1

    # Test 3: Update both
    try:
        store = VectorStore(dimension=384)
        v1 = np.random.rand(384).astype(np.float32)
        v2 = np.random.rand(384).astype(np.float32)
        vector_id = store.add_vector(v1, metadata={"a": 1})
        new_metadata = {"b": 2}
        result = store.update_vector(vector_id, vector=v2, metadata=new_metadata)
        assert result is True
        doc = store.get_vector(vector_id)
        assert np.array_equal(doc.vector, v2)
        assert doc.metadata == new_metadata
        print("✓ Update both vector and metadata")
        passed += 1
    except Exception as e:
        print(f"✗ Update both vector and metadata: {e}")
        failed += 1

    # Test 4: Update nonexistent
    try:
        store = VectorStore(dimension=384)
        vector = np.random.rand(384).astype(np.float32)
        result = store.update_vector("nonexistent", vector=vector)
        assert result is False
        print("✓ Update nonexistent vector")
        passed += 1
    except Exception as e:
        print(f"✗ Update nonexistent vector: {e}")
        failed += 1

    return passed, failed


def test_search():
    """Test search operations."""
    print("\n=== SEARCH TESTS ===")
    passed = 0
    failed = 0

    np.random.seed(42)

    # Test 1: Basic search
    try:
        store = VectorStore(dimension=384)
        vectors = [np.random.rand(384).astype(np.float32) for _ in range(3)]
        ids = store.add_vectors(vectors)
        results = store.similarity_search(vectors[0], k=3)
        assert len(results) == 3
        assert results[0][0].id == ids[0]
        assert results[0][1] > 0.99
        print("✓ Basic similarity search")
        passed += 1
    except Exception as e:
        print(f"✗ Basic similarity search: {e}")
        failed += 1

    # Test 2: Search with k
    try:
        store = VectorStore(dimension=384)
        vectors = [np.random.rand(384).astype(np.float32) for _ in range(3)]
        store.add_vectors(vectors)
        results = store.similarity_search(vectors[0], k=2)
        assert len(results) == 2
        print("✓ Search with k limit")
        passed += 1
    except Exception as e:
        print(f"✗ Search with k limit: {e}")
        failed += 1

    # Test 3: Search with filter
    try:
        store = VectorStore(dimension=384)
        vectors = [np.random.rand(384).astype(np.float32) for _ in range(3)]
        metadata = [
            {"category": "tech", "year": 2023},
            {"category": "science", "year": 2023},
            {"category": "tech", "year": 2024},
        ]
        store.add_vectors(vectors, metadatas=metadata)
        results = store.similarity_search(vectors[0], k=5, filter={"category": "tech"})
        assert len(results) == 2
        for doc, _ in results:
            assert doc.metadata["category"] == "tech"
        print("✓ Search with metadata filter")
        passed += 1
    except Exception as e:
        print(f"✗ Search with metadata filter: {e}")
        failed += 1

    # Test 4: Search with multiple filters
    try:
        store = VectorStore(dimension=384)
        vectors = [np.random.rand(384).astype(np.float32) for _ in range(3)]
        metadata = [
            {"category": "tech", "year": 2023},
            {"category": "science", "year": 2023},
            {"category": "tech", "year": 2024},
        ]
        store.add_vectors(vectors, metadatas=metadata)
        results = store.similarity_search(
            vectors[0], k=5, filter={"category": "tech", "year": 2024}
        )
        assert len(results) == 1
        assert results[0][0].metadata["year"] == 2024
        print("✓ Search with multiple filters")
        passed += 1
    except Exception as e:
        print(f"✗ Search with multiple filters: {e}")
        failed += 1

    # Test 5: Search with min score
    try:
        store = VectorStore(dimension=384)
        vectors = [np.random.rand(384).astype(np.float32) for _ in range(3)]
        store.add_vectors(vectors)
        results = store.similarity_search(vectors[0], k=10, min_score=0.99)
        assert len(results) == 1
        print("✓ Search with min score")
        passed += 1
    except Exception as e:
        print(f"✗ Search with min score: {e}")
        failed += 1

    # Test 6: Search empty store
    try:
        store = VectorStore(dimension=384)
        vector = np.random.rand(384).astype(np.float32)
        results = store.similarity_search(vector, k=5)
        assert len(results) == 0
        print("✓ Search empty store")
        passed += 1
    except Exception as e:
        print(f"✗ Search empty store: {e}")
        failed += 1

    # Test 7: Results sorted
    try:
        store = VectorStore(dimension=384)
        base_vector = np.ones(384, dtype=np.float32)
        similar_vector = base_vector + 0.1
        dissimilar_vector = -base_vector
        store.add_vectors([base_vector, similar_vector, dissimilar_vector])
        results = store.similarity_search(base_vector, k=3)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)
        print("✓ Search results sorted by score")
        passed += 1
    except Exception as e:
        print(f"✗ Search results sorted by score: {e}")
        failed += 1

    return passed, failed


def main():
    """Run all tests."""
    print("=" * 70)
    print("VECTOR STORE TEST SUITE")
    print("=" * 70)

    results = []
    results.append(test_insert())
    results.append(test_delete())
    results.append(test_update())
    results.append(test_search())

    total_passed = sum(r[0] for r in results)
    total_failed = sum(r[1] for r in results)

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
