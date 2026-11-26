"""Phase 3 Evaluation 2: Content Quality, ASCII Safety, Word Count & Readability.

Evaluates generated typing passages on three quantitative metrics:
  1. 100% Printable ASCII safety (0x20-0x7E) so every character can be typed on a standard keyboard.
  2. Word count bounds and complete sentence termination for short, medium, and long drills.
  3. Flesch-Kincaid Grade Level & average word length for typing ergonomics.
"""
import re
import pytest
from topics_router import CATALOG
from evals.conftest import flesch_kincaid_grade


ASCII_PRINTABLE_RE = re.compile(r"^[\x20-\x7E]+$")


@pytest.mark.parametrize(
    "domain,topic",
    [
        ("Programming", CATALOG["Programming"][0]),
        ("DBMS", CATALOG["DBMS"][0]),
        ("OS", CATALOG["OS"][0]),
    ],
)
def test_generated_passage_is_strictly_printable_ascii(eval_client, domain, topic):
    """Generated text must contain only printable ASCII characters (0x20-0x7E)."""
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
    data = resp.json()
    text = data["text"]
    question = data["question"]

    assert question and question.endswith("?"), f"Expected valid question ending with '?', got: {question!r}"
    assert "\n" not in question
    assert ASCII_PRINTABLE_RE.match(question), f"Non-ASCII chars found in question: {question!r}"
    assert ASCII_PRINTABLE_RE.match(text), f"Non-ASCII or control chars found in answer: {text!r}"
    # Specifically forbid smart quotes, em-dashes, ellipsis char, and raw tabs
    for forbidden in ["\u2018", "\u2019", "\u201c", "\u201d", "\u2013", "\u2014", "\u2026", "\t"]:
        assert forbidden not in text
        assert forbidden not in question


@pytest.mark.parametrize(
    "length_key,min_words,max_words",
    [
        ("short", 15, 55),
        ("medium", 35, 100),
        ("long", 65, 160),
    ],
)
def test_generated_passage_word_count_and_sentence_termination(
    eval_client, length_key, min_words, max_words
):
    """Passages must respect target word-count ranges and end on a complete sentence."""
    resp = eval_client.post(
        "/api/ai/generate",
        json={
            "domain": "Programming",
            "topic": CATALOG["Programming"][0],
            "difficulty": "Intermediate",
            "length": length_key,
            "include_code": False,
        },
    )
    assert resp.status_code == 200
    text = resp.json()["text"]
    words = text.split()
    word_count = len(words)

    assert min_words <= word_count <= max_words, (
        f"Length '{length_key}' produced {word_count} words (expected {min_words}-{max_words})"
    )
    assert text[-1] in ".!?", f"Passage did not end with sentence punctuation: {text!r}"


def test_generated_passage_readability_and_typing_ergonomics(eval_client):
    """Flesch-Kincaid grade level and average word length must stay within typeable ranges."""
    resp = eval_client.post(
        "/api/ai/generate",
        json={
            "domain": "OS",
            "topic": CATALOG["OS"][0],
            "difficulty": "Intermediate",
            "length": "medium",
            "include_code": False,
        },
    )
    assert resp.status_code == 200
    text = resp.json()["text"]

    fk_grade = flesch_kincaid_grade(text)
    words = text.split()
    avg_word_len = sum(len(w) for w in words) / len(words)

    # Technical CS content typically scores between Grade 6 and Grade 18
    assert 4.0 <= fk_grade <= 20.0, f"Flesch-Kincaid grade {fk_grade} outside readable range"
    assert 3.5 <= avg_word_len <= 9.0, f"Average word length {avg_word_len:.2f} abnormal"
