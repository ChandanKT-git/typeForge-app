"""Document upload, chunking, retrieval, and RAG drill generation router.

WHY THIS MODULE EXISTS:
  Enables TypeForge users to upload custom learning materials (notes, code,
  documentation, textbooks) and convert them into interactive typing drills.
  Provides two modes:
    1. Direct Mode: Select individual parsed chunks to type verbatim.
    2. AI Drill Mode (RAG): Retrieve relevant context chunks based on a query
       and prompt the LLM to generate an educational typing passage strictly
       grounded in the uploaded material.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from auth import get_current_user
from text_processing import PARSERS, chunk_text, sanitize_for_typing

router = APIRouter(prefix="/documents", tags=["documents"])

# --- Embedding Model (Lazy-loaded singleton with fallback) ---

_embedder = None
EMBEDDING_DIM = 384


def _get_embedder():
    """Lazy-load the SentenceTransformer embedding model.

    If sentence-transformers is installed, loads all-MiniLM-L6-v2 (384 dims).
    Returns None if sentence-transformers is not available.
    """
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer

            model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            _embedder = SentenceTransformer(model_name)
        except Exception:
            _embedder = False
    return _embedder if _embedder is not False else None


def _fallback_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Lightweight deterministic feature embedding used if PyTorch/SentenceTransformers
    is unavailable. Maps character and word n-grams into a normalized unit vector.
    """
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    for w in words:
        h = hash(w) % dim
        vec[h] += 1.0
        # Character bigrams
        for i in range(len(w) - 1):
            bg_h = hash(w[i : i + 2]) % dim
            vec[bg_h] += 0.5
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate 384-dimensional embedding vectors for a list of strings.

    Uses sentence-transformers if available; otherwise falls back to
    deterministic normalized n-gram vectors. All vectors are L2-normalized.
    """
    model = _get_embedder()
    if model is not None:
        vectors = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vectors]
    return [_fallback_embedding(t) for t in texts]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two float vectors.

    Values range between -1.0 and 1.0, where 1.0 indicates identical vectors.
    """
    a_np = np.array(a, dtype=np.float32)
    b_np = np.array(b, dtype=np.float32)
    dot = np.dot(a_np, b_np)
    norm = np.linalg.norm(a_np) * np.linalg.norm(b_np)
    if norm == 0:
        return 0.0
    return float(dot / norm)


# --- Schemas ---

class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    total_chunks: int
    total_words: int
    uploaded_at: str


class ChunkOut(BaseModel):
    id: str
    document_id: str
    index: int
    text: str
    word_count: int


class DocumentDetailOut(BaseModel):
    document: DocumentOut
    chunks: List[ChunkOut]


class GenerateFromDocIn(BaseModel):
    document_id: str
    query: Optional[str] = Field(
        None,
        description="Optional focus query (e.g. 'B-Trees', 'Concurrency'). If omitted, uses leading document chunks.",
    )
    difficulty: str = "Intermediate"
    length: str = "medium"
    bypass_cache: bool = False


class GenerateFromDocOut(BaseModel):
    question: Optional[str] = None
    text: str
    notes: List[str]
    source_chunks: List[int]
    domain: str
    topic: str
    difficulty: str
    mode: Literal["qa", "passage"] = "qa"


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = set(PARSERS.keys())


# --- Endpoints ---

@router.post("", response_model=DocumentOut)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a document, parse text, chunk into typing passages, embed chunks,
    and persist metadata and chunks in MongoDB.
    """
    db = request.app.state.db

    filename = file.filename or "untitled.txt"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    parser = PARSERS[ext]
    try:
        raw_text = parser(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")

    if not raw_text or len(raw_text.split()) < 10:
        raise HTTPException(
            status_code=422,
            detail="Could not extract enough text from this file. For scanned PDFs, use a text-based PDF.",
        )

    chunks = chunk_text(raw_text)
    if not chunks:
        raise HTTPException(status_code=422, detail="File produced no usable typing chunks.")

    # Generate embeddings for all chunks in batch
    embeddings = embed_texts(chunks)

    doc_id = str(uuid.uuid4())
    total_words = sum(len(c.split()) for c in chunks)
    doc_meta = {
        "id": doc_id,
        "user_id": user["id"],
        "filename": filename,
        "file_type": ext,
        "total_chunks": len(chunks),
        "total_words": total_words,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.documents.insert_one(doc_meta)

    chunk_docs = []
    for i, (chunk_text_str, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_docs.append(
            {
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "user_id": user["id"],
                "index": i,
                "text": chunk_text_str,
                "word_count": len(chunk_text_str.split()),
                "embedding": embedding,
            }
        )
    if chunk_docs:
        await db.document_chunks.insert_many(chunk_docs)

    return DocumentOut(**{k: doc_meta[k] for k in DocumentOut.model_fields})


@router.get("", response_model=List[DocumentOut])
async def list_documents(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """List all documents uploaded by the current authenticated user."""
    db = request.app.state.db
    cursor = db.documents.find({"user_id": user["id"]}, {"_id": 0}).sort("uploaded_at", -1)
    docs = await cursor.to_list(100)
    return [DocumentOut(**{k: d[k] for k in DocumentOut.model_fields}) for d in docs]


@router.get("/{doc_id}", response_model=DocumentDetailOut)
async def get_document(
    doc_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Retrieve document details and all chunk passages for typing."""
    db = request.app.state.db
    doc = await db.documents.find_one({"id": doc_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_cursor = db.document_chunks.find(
        {"document_id": doc_id},
        {"_id": 0, "embedding": 0},  # Exclude embedding vector from frontend payload
    ).sort("index", 1)
    chunks = await chunk_cursor.to_list(500)

    return DocumentDetailOut(
        document=DocumentOut(**{k: doc[k] for k in DocumentOut.model_fields}),
        chunks=[ChunkOut(**{k: c[k] for k in ChunkOut.model_fields}) for c in chunks],
    )


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Delete a document and all its associated chunks."""
    db = request.app.state.db
    doc = await db.documents.find_one({"id": doc_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.document_chunks.delete_many({"document_id": doc_id})
    await db.documents.delete_one({"id": doc_id})
    return {"deleted": True}

@router.post("/generate-drill", response_model=GenerateFromDocOut)
async def generate_drill_from_document(
    payload: GenerateFromDocIn,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """RAG endpoint: retrieve context chunks relevant to the user query and generate
    an educational typing drill grounded solely in the document content.
    """
    db = request.app.state.db

    doc = await db.documents.find_one({"id": payload.document_id, "user_id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks_cursor = db.document_chunks.find({"document_id": payload.document_id}, {"_id": 0}).sort("index", 1)
    all_chunks = await chunks_cursor.to_list(500)

    if not all_chunks:
        raise HTTPException(status_code=422, detail="Document has no chunks")

    # --- Retrieval Step ---
    TOP_K = 3
    if payload.query and payload.query.strip():
        query_embedding = embed_texts([payload.query.strip()])[0]
        scored = []
        for chunk in all_chunks:
            chunk_emb = chunk.get("embedding")
            if chunk_emb:
                sim = cosine_similarity(query_embedding, chunk_emb)
            else:
                sim = 0.0
            scored.append((sim, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected_chunks = [c for _, c in scored[:TOP_K]]
    else:
        selected_chunks = all_chunks[:TOP_K]

    # --- Augmentation Step ---
    context_parts = [c["text"] for c in selected_chunks]
    source_indices = [c["index"] for c in selected_chunks]
    context_str = "\n\n---\n\n".join(context_parts)

    # --- Generation Step (Grounded Q&A Mode) ---
    import re
    from ai_service import QALLMResponse, _chat_structured

    length_map = {"short": "25-40 words", "medium": "50-80 words", "long": "90-130 words"}
    target_len = length_map.get(payload.length.lower(), "50-80 words")

    system = (
        "You are a curriculum author for a typing-while-learning application. "
        "You craft a sharp concept-check question and a clean, typing-friendly model answer. "
        "You MUST base both the question and the answer strictly on the provided context excerpts. "
        "Do not invent facts not present in the context. "
        "Output strict JSON only with no markdown or external commentary."
    )

    user_msg = f"""
Generate a Concept Q&A typing practice drill based ONLY on the following document excerpts.

CONTEXT FROM USER'S DOCUMENT:
\"\"\"{context_str}\"\"\"

Requirements:
- Difficulty: {payload.difficulty}
- Answer target length: {target_len}
- `question`: ONE single-line question ending with '?' that is directly answered by the context excerpts.
- `text` (the model answer):
  - Directly answer the question in a single continuous paragraph of {target_len} using ONLY facts from the context.
  - Do not start with conversational filler ("Sure", "The answer is", etc.) and do not use bullet points.
  - Use only standard keyboard ASCII characters (letters, numbers, basic punctuation).
- `notes`: Provide 3 concise bullet notes summarizing what is learned.

Return JSON:
{{"question": "<question ending with ?>", "text": "<model answer passage>", "notes": ["note 1", "note 2", "note 3"]}}
""".strip()

    result = _chat_structured(
        system,
        user_msg,
        response_model=QALLMResponse,
        max_tokens=900,
        temperature=0.5,
        trace_name="rag_generate_drill",
        user_id=user.get("id"),
        trace_metadata={
            "document_id": payload.document_id,
            "filename": doc["filename"],
            "query": payload.query,
            "difficulty": payload.difficulty,
            "source_chunks": source_indices,
            "mode": "qa",
        },
    )
    question = sanitize_for_typing(result.question.strip())
    question = re.sub(r"\s+", " ", question).strip()
    if not question.endswith("?"):
        question = question.rstrip(".!") + "?"

    text = sanitize_for_typing(result.text.strip())
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        raise HTTPException(status_code=502, detail="AI could not generate from document")

    return GenerateFromDocOut(
        question=question,
        text=text,
        notes=[str(n) for n in result.notes][:5],
        source_chunks=source_indices,
        domain="Custom Document",
        topic=doc["filename"],
        difficulty=payload.difficulty,
        mode="qa",
    )
