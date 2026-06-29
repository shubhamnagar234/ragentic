from typing import List
from sentence_transformers import SentenceTransformer
from app.services.ingestion.chunker import Chunk

# Load model once at module level — avoids reloading on every call
TEXT_MODEL_NAME = "BAAI/bge-large-en-v1.5"
CODE_MODEL_NAME = "nomic-ai/nomic-embed-text-v1"

_text_model = None
_code_model = None


def get_text_model() -> SentenceTransformer:
    global _text_model
    if _text_model is None:
        print(f"[embedder] Loading text model: {TEXT_MODEL_NAME}")
        _text_model = SentenceTransformer(TEXT_MODEL_NAME)
    return _text_model


def get_code_model() -> SentenceTransformer:
    global _code_model
    if _code_model is None:
        print(f"[embedder] Loading code model: {CODE_MODEL_NAME}")
        _code_model = SentenceTransformer(CODE_MODEL_NAME, trust_remote_code=True)
    return _code_model


def embed_chunks(
    chunks: List[Chunk],
    is_code: bool = False,
) -> List[dict]:
    """
    Embeds a list of chunks and returns them with their vectors.
    Only embeds child chunks — parent chunks are stored in PostgreSQL for context retrieval.
    Returns list of dicts ready for Qdrant upsert.
    """
    # Filter to child chunks only for embedding
    child_chunks = [c for c in chunks if c.chunk_type == "child"]

    if not child_chunks:
        return []

    texts = [c.text for c in child_chunks]

    # Choose model based on content type
    model = get_code_model() if is_code else get_text_model()

    print(f"[embedder] Embedding {len(texts)} child chunks...")
    vectors = model.encode(texts, batch_size=32, show_progress_bar=True)

    results = []
    for chunk, vector in zip(child_chunks, vectors):
        results.append({
            "chunk_id": chunk.chunk_id,
            "parent_id": chunk.parent_id,
            "text": chunk.text,
            "vector": vector.tolist(),
            "page_num": chunk.page_num,
            "start_time": chunk.start_time,
            "end_time": chunk.end_time,
            "metadata": chunk.metadata,
        })

    return results


def embed_query(query: str, is_code: bool = False) -> List[float]:
    """
    Embeds a single query string for retrieval.
    """
    model = get_code_model() if is_code else get_text_model()
    vector = model.encode(query)
    return vector.tolist()