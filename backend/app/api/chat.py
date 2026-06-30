import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import get_current_user
from app.models.workspace import Workspace
from app.models.message import Message
from app.schemas.chat import ChatRequest
from app.services.agents.graph import ragentic_graph
from app.services.memory.compressor import get_conversation_memory

router = APIRouter()


async def verify_workspace(
    workspace_id: str,
    user_id: str,
    db: AsyncSession,
) -> Workspace:
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


async def event_generator(
    query: str,
    workspace_id: str,
    user_id: str,
    source_ids: list,
    db: AsyncSession,
):
    """
    SSE event generator — runs the agent graph and streams events.
    Event types:
    - timeline: agent status updates
    - token: streamed response tokens
    - sources: cited sources
    - confidence: confidence level
    - done: stream complete
    """
    try:
        # Get conversation memory
        memory = await get_conversation_memory(
            session_id=workspace_id,
            db=db,
        )

        # Build initial state
        initial_state = {
            "query": query,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "source_ids": [str(s) for s in source_ids] if source_ids else None,
            "query_type": "",
            "vector_weight": 0.6,
            "bm25_weight": 0.4,
            "top_k": 20,
            "dense_chunks": [],
            "sparse_chunks": [],
            "fused_chunks": [],
            "reranked_chunks": [],
            "faithfulness_score": None,
            "context_precision": None,
            "answer_relevance": None,
            "confidence_level": "MEDIUM",
            "retry_count": 0,
            "conversation_summary": memory.summary,
            "recent_turns": memory.recent_turns,
            "final_answer": "",
            "sources_used": [],
            "timeline_events": [],
            "action_items": [],
            "report": None,
        }

        # Stream timeline events as graph runs
        seen_events = 0

        async for state in ragentic_graph.astream(initial_state):
            # Get new timeline events
            all_events = []
            for node_output in state.values():
                if isinstance(node_output, dict):
                    all_events = node_output.get("timeline_events", [])

            # Stream new events
            new_events = all_events[seen_events:]
            for event in new_events:
                yield f"data: {json.dumps({'type': 'timeline', 'data': event})}\n\n"
                seen_events += 1

        # Get final state
        final_state = None
        async for final_state in ragentic_graph.astream(initial_state):
            pass

        if final_state:
            for node_output in final_state.values():
                if isinstance(node_output, dict) and node_output.get("final_answer"):
                    answer = node_output["final_answer"]
                    sources = node_output.get("sources_used", [])
                    confidence = node_output.get("confidence_level", "MEDIUM")

                    # Stream answer tokens
                    words = answer.split()
                    for i, word in enumerate(words):
                        token = word + (" " if i < len(words) - 1 else "")
                        yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"

                    # Send sources
                    yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"

                    # Send confidence
                    yield f"data: {json.dumps({'type': 'confidence', 'data': confidence})}\n\n"

                    # Save messages to DB
                    user_msg = Message(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        role="user",
                        content=query,
                    )
                    assistant_msg = Message(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        role="assistant",
                        content=answer,
                        sources=sources,
                        confidence=confidence,
                    )
                    db.add(user_msg)
                    db.add(assistant_msg)
                    await db.commit()

        # Send done event
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        print(f"[chat] Stream error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"


@router.post("/{workspace_id}/chat")
async def chat(
    workspace_id: str,
    payload: ChatRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace(workspace_id, user_id, db)

    return StreamingResponse(
        event_generator(
            query=payload.query,
            workspace_id=workspace_id,
            user_id=user_id,
            source_ids=payload.source_ids or [],
            db=db,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
