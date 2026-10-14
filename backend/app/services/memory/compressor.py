from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ConversationMemory:
    summary: str
    recent_turns: List[dict]
    turn_count: int


async def compress_conversation(
    turns: List[dict],
) -> str:
    """
    Compresses a list of conversation turns into a rolling summary.
    Called every 5 turns to keep context window bounded.
    turns: [{"role": "user"|"assistant", "content": str}]
    Returns summary string.
    """
    from app.services.llm.client import get_llm_response

    if not turns:
        return ""

    # Format turns for compression
    formatted = "\n".join([f"{t['role'].upper()}: {t['content']}" for t in turns])

    prompt = f"""Summarize this conversation in 2-3 sentences.
Focus on key topics discussed, decisions made, and important context.
Be concise — this summary will be used as memory for future responses.

Conversation:
{formatted}

Summary:"""

    try:
        summary = await get_llm_response(prompt, max_tokens=200)
        print(f"[compressor] Compressed {len(turns)} turns into summary")
        return summary.strip()

    except Exception as e:
        print(f"[compressor] Compression failed: {e}")
        return ""


async def get_conversation_memory(
    session_id: str,
    db,
    keep_last_n: int = 3,
    compress_after: int = 5,
) -> ConversationMemory:
    """
    Retrieves conversation memory for a session.
    - If turn count is multiple of compress_after → compress older turns
    - Always keeps last keep_last_n turns raw
    Returns ConversationMemory with summary + recent turns.
    """
    from sqlalchemy import select, asc
    from app.models.message import Message

    # Fetch all messages for this session
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(asc(Message.created_at))
    )
    messages = result.scalars().all()

    if not messages:
        return ConversationMemory(
            summary="",
            recent_turns=[],
            turn_count=0,
        )

    turn_count = len(messages)
    turns = [{"role": m.role, "content": m.content} for m in messages]

    # Keep last N turns raw
    recent_turns = turns[-keep_last_n:]
    older_turns = turns[:-keep_last_n]

    # Compress older turns if enough history
    summary = ""
    if len(older_turns) >= compress_after:
        summary = await compress_conversation(older_turns)
        print(
            f"[compressor] Memory compressed: {turn_count} turns -> summary + {len(recent_turns)} recent"
        )

    return ConversationMemory(
        summary=summary,
        recent_turns=recent_turns,
        turn_count=turn_count,
    )
