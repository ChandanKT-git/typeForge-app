"""Document parsing, text sanitization, and intelligent chunking for TypeForge.

WHY THIS MODULE EXISTS:
  TypeForge typing passages need to be 25–130 words of clean, ASCII-safe text.
  Users upload real-world documents (PDFs, Markdown notes, source code, plain text).
  This module bridges that gap:
    1. Parses diverse file formats into raw text.
    2. Sanitizes characters to printable ASCII safe for keyboard entry.
    3. Splits text into typing-friendly chunks along natural sentence boundaries.
"""

import io
import re
from typing import List


# --- Parsers ---

def parse_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using pypdf.

    pypdf is pure-Python and does not require C-extensions or external
    system libraries, making it easy to run and deploy.
    """
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages: List[str] = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            pages.append(extracted)
    return "\n\n".join(pages)


def parse_markdown(file_bytes: bytes) -> str:
    """Convert Markdown to plain text by stripping markdown formatting syntax.

    Retains inline identifiers and code content while stripping structural
    markup, headers, and image references.
    """
    text = file_bytes.decode("utf-8", errors="replace")

    # Remove code fence markers (```lang ... ```) but preserve inner code content
    text = re.sub(r"```[\w]*\n?", "", text)

    # Remove image syntax: ![alt](url)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)

    # Convert links [text](url) to just 'text'
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove heading markers (# Heading -> Heading)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Remove bold and italic markers (*word* or **word** or _word_)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", text)

    # Remove blockquote markers (> Quote -> Quote)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)

    # Remove horizontal rules (---, ***, ___)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Remove inline code backticks (`code` -> code)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    return text


def parse_plaintext(file_bytes: bytes) -> str:
    """Decode raw text or code files, handling UTF-8 with optional BOM."""
    return file_bytes.decode("utf-8-sig", errors="replace")


# Map of file extension -> parser function
PARSERS = {
    ".pdf": parse_pdf,
    ".md": parse_markdown,
    ".markdown": parse_markdown,
    ".txt": parse_plaintext,
    ".py": parse_plaintext,
    ".js": parse_plaintext,
    ".ts": parse_plaintext,
    ".jsx": parse_plaintext,
    ".tsx": parse_plaintext,
    ".go": parse_plaintext,
    ".rs": parse_plaintext,
    ".java": parse_plaintext,
    ".c": parse_plaintext,
    ".cpp": parse_plaintext,
    ".h": parse_plaintext,
    ".sql": parse_plaintext,
    ".sh": parse_plaintext,
    ".yaml": parse_plaintext,
    ".yml": parse_plaintext,
    ".json": parse_plaintext,
    ".toml": parse_plaintext,
    ".csv": parse_plaintext,
}


# --- ASCII Sanitization ---

def sanitize_for_typing(text: str) -> str:
    """Clean text to ensure every character can be typed on a standard keyboard.

    Replaces smart quotes, curly apostrophes, dashes, ellipses, and tabs.
    Strips non-printable and non-ASCII characters that would cause TypingArena
    rendering or input mismatch issues.
    """
    text = (
        text.replace("\u2018", "'").replace("\u2019", "'")     # Smart single quotes
        .replace("\u201c", '"').replace("\u201d", '"')          # Smart double quotes
        .replace("\u2013", "-").replace("\u2014", "-")          # En-dash, em-dash
        .replace("\u2026", "...")                                # Ellipsis
        .replace("\t", "    ")                                  # Tabs -> 4 spaces
    )
    # Strip any remaining characters outside printable ASCII and basic whitespace
    text = re.sub(r"[^\x0A\x0D\x20-\x7E]", "", text)
    return text


# --- Chunking ---

def chunk_text(
    text: str,
    min_words: int = 30,
    max_words: int = 100,
    target_words: int = 60,
) -> List[str]:
    """Split a long text document into typing-practice-sized chunks.

    ALGORITHM:
      1. Sanitize text and collapse superfluous whitespace.
      2. Split text into sentences using positive lookbehind regex (?<=[.!?])\\s+.
         This guarantees passages don't cut off mid-sentence.
      3. Greedily aggregate sentences into chunks aiming for `target_words`,
         never exceeding `max_words` unless a single sentence is longer.
      4. If the final chunk is smaller than `min_words`, merge it into the
         previous chunk.
    """
    text = sanitize_for_typing(text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()

    if not text:
        return []

    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text] if len(text.split()) >= min_words else []

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        # If a single sentence exceeds max_words, finalize current chunk and
        # append the sentence as its own passage
        if sentence_words > max_words:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_word_count = 0
            chunks.append(sentence)
            continue

        # If adding this sentence exceeds max_words, finalize the current chunk
        if current_word_count + sentence_words > max_words and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_word_count = 0

        current_chunk.append(sentence)
        current_word_count += sentence_words

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    # Merge tiny trailing chunk into preceding chunk if available
    if len(chunks) > 1 and len(chunks[-1].split()) < min_words:
        last = chunks.pop()
        chunks[-1] = chunks[-1] + " " + last

    # Final normalization
    cleaned_chunks: List[str] = []
    for c in chunks:
        norm = re.sub(r"\s+", " ", c).strip()
        if len(norm.split()) >= 5:
            cleaned_chunks.append(norm)

    return cleaned_chunks
