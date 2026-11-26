"""Unit tests for text_processing module (parsers, sanitization, chunking)."""
import pytest
from text_processing import (
    parse_markdown,
    parse_plaintext,
    sanitize_for_typing,
    chunk_text,
    PARSERS,
)


def test_parse_markdown_removes_formatting_retains_identifiers():
    raw_md = b"# Section Header\nHere is **important** text with `variable_name`.\n- Item 1\n- Item 2\n> A quote"
    parsed = parse_markdown(raw_md)
    assert "# Section Header" not in parsed
    assert "Section Header" in parsed
    assert "**important**" not in parsed
    assert "important" in parsed
    assert "`variable_name`" not in parsed
    assert "variable_name" in parsed
    assert "> A quote" not in parsed
    assert "A quote" in parsed


def test_parse_plaintext():
    raw_bytes = b"def hello_world():\n    return 'ok'\n"
    parsed = parse_plaintext(raw_bytes)
    assert "def hello_world():" in parsed


def test_parsers_extension_coverage():
    for ext in [".pdf", ".md", ".txt", ".py", ".js", ".json"]:
        assert ext in PARSERS
        assert callable(PARSERS[ext])


def test_sanitize_for_typing_replaces_smart_quotes_and_symbols():
    dirty = "“Smart quotes” and ‘single’ with em—dash and ellipsis… and\ttab"
    clean = sanitize_for_typing(dirty)
    assert '“' not in clean and '”' not in clean
    assert '"Smart quotes"' in clean
    assert "‘" not in clean and "’" not in clean
    assert "'single'" in clean
    assert "—" not in clean
    assert "-" in clean
    assert "…" not in clean
    assert "..." in clean
    assert "\t" not in clean
    assert "    " in clean


def test_chunk_text_splits_on_sentence_boundaries():
    text = (
        "Operating systems manage hardware resources efficiently. "
        "Virtual memory gives processes the illusion of contiguous RAM. "
        "Paging divides memory into fixed-sized blocks called frames and pages. "
        "Segmentation divides address spaces into variable logical segments. "
        "Page tables translate virtual addresses to physical memory addresses."
    )
    chunks = chunk_text(text, min_words=10, max_words=30, target_words=20)
    assert len(chunks) >= 2
    for chunk in chunks:
        # Every chunk should end with sentence punctuation or alphanumeric
        assert chunk.endswith((".", "!", "?"))
        # Verify word counts are within limits
        word_count = len(chunk.split())
        assert word_count >= 5
