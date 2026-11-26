"""Phase 3 Evaluation 3: Factual Accuracy via LLM-as-Judge.

Uses a structured LLM-as-Judge rubric (1-5 scale) to verify that generated
typing passages teach accurate computer science concepts, and includes a
negative control test to ensure the judge penalizes technical hallucinations.
"""
import pytest
from topics_router import CATALOG
from evals.conftest import llm_judge_factual_accuracy


@pytest.mark.parametrize(
    "domain,topic",
    [
        ("Programming", CATALOG["Programming"][0]),
        ("DBMS", CATALOG["DBMS"][0]),
        ("OS", CATALOG["OS"][0]),
        ("Networking", CATALOG["Networking"][0]),
    ],
)
def test_generated_passage_passes_factual_accuracy_judge(eval_client, domain, topic):
    """Generated CS passages must score >= 4/5 on the LLM-as-Judge factual accuracy rubric."""
    resp = eval_client.post(
        "/api/ai/generate",
        json={
            "domain": domain,
            "topic": topic,
            "difficulty": "Intermediate",
            "length": "medium",
            "include_code": False,
        },
    )
    assert resp.status_code == 200
    passage = resp.json()["text"]

    verdict = llm_judge_factual_accuracy(domain=domain, topic=topic, passage=passage)
    assert verdict.score >= 4, (
        f"Factual accuracy score {verdict.score}/5 too low for {domain}/{topic}: {verdict.reasoning}"
    )
    assert verdict.is_accurate is True


def test_factual_judge_penalizes_hallucinated_misconception():
    """Negative control: the factual judge must score a blatantly wrong CS passage <= 2/5."""
    hallucinated_passage = (
        "TCP is a connectionless protocol that never guarantees delivery or packet ordering. "
        "It blasts raw datagrams across the network without handshakes, acknowledgments, or congestion control."
    )
    verdict = llm_judge_factual_accuracy(
        domain="Networking",
        topic="TCP vs UDP",
        passage=hallucinated_passage,
    )
    assert verdict.score <= 2, f"Expected judge to penalize hallucination, got {verdict.score}/5"
    assert verdict.is_accurate is False
