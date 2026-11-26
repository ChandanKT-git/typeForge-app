"""Phase 3 Evaluation 4: RAG Grounding & Faithfulness.

Verifies that `/api/documents/generate-drill` retrieves relevant chunks from
the uploaded document and generates a passage strictly grounded in those
chunks (scoring >= 4/5 on the RAG Grounding Judge rubric).
"""
from evals.conftest import BTREE_DOCUMENT_CONTENT, llm_judge_rag_grounding


def test_rag_drill_is_grounded_in_document_context(eval_client, seeded_document_id):
    """RAG-generated passage must stay grounded in the uploaded B-Tree document."""
    resp = eval_client.post(
        "/api/documents/generate-drill",
        json={
            "document_id": seeded_document_id,
            "query": "B-Tree disk I/O and logarithmic lookups",
            "difficulty": "Intermediate",
            "length": "medium",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    question = data["question"]
    passage = data["text"]

    # 1. Verify Q&A mode, question format, and source chunk indices
    assert data["mode"] == "qa"
    assert question and question.endswith("?")
    assert len(data["source_chunks"]) >= 1

    # 2. Evaluate grounding faithfulness of both Question and Answer with LLM-as-Judge
    context_text = BTREE_DOCUMENT_CONTENT.decode("utf-8")
    combined_qa = f"Q: {question}\nA: {passage}"
    verdict = llm_judge_rag_grounding(context=context_text, passage=combined_qa)

    assert verdict.score >= 4, (
        f"RAG grounding score {verdict.score}/5 is below threshold: {verdict.reasoning}"
    )
    assert verdict.is_grounded is True


def test_rag_grounding_judge_rejects_ungrounded_off_topic_passage():
    """Negative control: an off-topic passage unrelated to the document context must score <= 2/5."""
    context_text = BTREE_DOCUMENT_CONTENT.decode("utf-8")
    ungrounded_passage = (
        "Convolutional neural networks apply learnable spatial filters across image tensors "
        "to detect edges, textures, and high-level visual object categories in computer vision."
    )

    verdict = llm_judge_rag_grounding(context=context_text, passage=ungrounded_passage)
    assert verdict.score <= 2, f"Expected off-topic passage to fail grounding, got {verdict.score}/5"
    assert verdict.is_grounded is False
