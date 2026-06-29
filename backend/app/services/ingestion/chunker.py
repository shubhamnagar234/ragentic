from typing import List
from dataclasses import dataclass, field
import uuid


@dataclass
class Chunk:
    text: str
    chunk_type: str           # "parent" or "child"
    parent_id: str = None
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    page_num: int = None      # for PDFs
    start_time: float = None  # for audio/video
    end_time: float = None    # for audio/video
    metadata: dict = field(default_factory=dict)


def chunk_text_hierarchical(
    text: str,
    parent_chunk_size: int = 1000,
    child_chunk_size: int = 150,
    overlap: int = 20,
) -> List[Chunk]:
    """
    Hierarchical chunking strategy:
    - Parent chunks: ~1000 tokens for rich LLM context
    - Child chunks: ~150 tokens for precise retrieval
    Each child stores its parent_id for lookup.
    """
    chunks = []

    # Split into parent chunks
    parent_chunks = _split_text(text, parent_chunk_size, overlap)

    for parent_text in parent_chunks:
        parent_id = str(uuid.uuid4())

        # Create parent chunk
        parent = Chunk(
            text=parent_text,
            chunk_type="parent",
            chunk_id=parent_id,
            parent_id=None,
        )
        chunks.append(parent)

        # Split parent into child chunks
        child_texts = _split_text(parent_text, child_chunk_size, overlap)
        for child_text in child_texts:
            child = Chunk(
                text=child_text,
                chunk_type="child",
                parent_id=parent_id,
            )
            chunks.append(child)

    return chunks


def chunk_transcript_hierarchical(
    segments: List[dict],
    parent_duration: float = 120.0,  # 2 minutes per parent
    child_duration: float = 30.0,    # 30 seconds per child
) -> List[Chunk]:
    """
    Hierarchical chunking for audio/video transcripts.
    Groups segments by time window into parent and child chunks.
    segments: [{text, start, end}]
    """
    chunks = []

    if not segments:
        return chunks

    # Group segments into parent time windows
    parent_groups = _group_segments_by_duration(segments, parent_duration)

    for parent_group in parent_groups:
        parent_text = " ".join([s["text"] for s in parent_group])
        parent_start = parent_group[0]["start"]
        parent_end = parent_group[-1]["end"]
        parent_id = str(uuid.uuid4())

        parent = Chunk(
            text=parent_text,
            chunk_type="parent",
            chunk_id=parent_id,
            start_time=parent_start,
            end_time=parent_end,
        )
        chunks.append(parent)

        # Split parent group into child time windows
        child_groups = _group_segments_by_duration(parent_group, child_duration)
        for child_group in child_groups:
            child_text = " ".join([s["text"] for s in child_group])
            child = Chunk(
                text=child_text,
                chunk_type="child",
                parent_id=parent_id,
                start_time=child_group[0]["start"],
                end_time=child_group[-1]["end"],
            )
            chunks.append(child)

    return chunks


def _split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Splits text into chunks of approximately chunk_size words with overlap.
    """
    words = text.split()
    result = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        result.append(chunk)
        start += chunk_size - overlap

    return result


def _group_segments_by_duration(
    segments: List[dict], max_duration: float
) -> List[List[dict]]:
    """
    Groups transcript segments into time windows of max_duration seconds.
    """
    groups = []
    current_group = []
    group_start = None

    for segment in segments:
        if group_start is None:
            group_start = segment["start"]

        current_duration = segment["end"] - group_start

        if current_duration > max_duration and current_group:
            groups.append(current_group)
            current_group = [segment]
            group_start = segment["start"]
        else:
            current_group.append(segment)

    if current_group:
        groups.append(current_group)

    return groups