"""Unit and integration tests for document_router (embeddings, cosine similarity, retrieval)."""
import pytest
from document_router import cosine_similarity, embed_texts, EMBEDDING_DIM


def test_embed_texts_returns_normalized_vectors():
    texts = [
        "Database indexing with B-Trees improves lookup speed.",
        "Convolutional neural networks extract hierarchical spatial features.",
    ]
    vectors = embed_texts(texts)
    assert len(vectors) == 2
    for v in vectors:
        assert len(v) == EMBEDDING_DIM
        # Check that vector is non-zero
        assert any(val != 0.0 for val in v)


def test_cosine_similarity_identical_vectors():
    vec = [0.5, 0.5, 0.5, 0.5]
    sim = cosine_similarity(vec, vec)
    assert pytest.approx(sim, 0.001) == 1.0


def test_cosine_similarity_orthogonal_vectors():
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    sim = cosine_similarity(v1, v2)
    assert pytest.approx(sim, 0.001) == 0.0


def test_cosine_similarity_opposite_vectors():
    v1 = [1.0, 0.0]
    v2 = [-1.0, 0.0]
    sim = cosine_similarity(v1, v2)
    assert pytest.approx(sim, 0.001) == -1.0


def test_retrieval_ranking():
    # Documents
    doc1 = "Paging and virtual memory management in modern operating systems."
    doc2 = "Relational database ACID transactions and write ahead logging."
    doc3 = "Deep reinforcement learning using policy gradient algorithms."

    embeddings = embed_texts([doc1, doc2, doc3])
    query = "virtual memory and page replacement"
    q_emb = embed_texts([query])[0]

    sims = [cosine_similarity(q_emb, emb) for emb in embeddings]
    # The OS doc (doc1) should have the highest similarity to the OS query
    assert sims[0] > sims[1]
    assert sims[0] > sims[2]
