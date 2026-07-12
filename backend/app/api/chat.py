from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc
import json
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.workspace import Workspace
from app.models.message import Message
from app.schemas.chat import ChatRequest, MessageResponse, MessageFeedbackRequest
from app.services.agents.graph import ragentic_graph
from app.services.memory.compressor import get_conversation_memory
from app.services.llm.client import get_llm_response
from app.models.session import Session

router = APIRouter()


async def verify_workspace(
    workspace_id: str,
    user_id: str,
    db: AsyncSession,
) -> Workspace:
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == UUID(user_id),
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


@router.get(
    "/{workspace_id}/messages",
    response_model=list[MessageResponse],
)
async def get_messages(
    workspace_id: str,
    session_id: Optional[str] = None,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace(workspace_id, user_id, db)

    query = select(Message).where(Message.workspace_id == workspace_id)
    if session_id:
        query = query.where(Message.session_id == UUID(session_id))
    
    result = await db.execute(query.order_by(asc(Message.created_at)))
    return result.scalars().all()


@router.delete(
    "/{workspace_id}/messages",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_messages(
    workspace_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace(workspace_id, user_id, db)

    result = await db.execute(
        select(Message).where(Message.workspace_id == workspace_id)
    )
    messages = result.scalars().all()
    for msg in messages:
        await db.delete(msg)
    await db.commit()

@router.patch(
    "/{workspace_id}/messages/{message_id}/feedback",
    response_model=MessageResponse,
)
async def update_message_feedback(
    workspace_id: str,
    message_id: str,
    payload: MessageFeedbackRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace(workspace_id, user_id, db)

    result = await db.execute(
        select(Message).where(
            Message.id == message_id,
            Message.workspace_id == workspace_id
        )
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )
        
    message.feedback = payload.feedback
    await db.commit()
    await db.refresh(message)
    
    return message


async def event_generator(
    query: str,
    workspace_id: str,
    session_id: Optional[str],
    user_id: str,
    source_ids: list,
    db: AsyncSession,
):
    try:
        memory = await get_conversation_memory(
            session_id=session_id or workspace_id,
            db=db,
        )

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

        seen_events = 0
        final_state = None

        # Single astream pass: emit timeline events incrementally
        # and retain the last state snapshot for the final answer.
        async for state in ragentic_graph.astream(initial_state):
            final_state = state  # always keep the latest state

            all_events = []
            for node_output in state.values():
                if isinstance(node_output, dict):
                    all_events = node_output.get("timeline_events", [])

            new_events = all_events[seen_events:]
            for event in new_events:
                yield f"data: {json.dumps({'type': 'timeline', 'data': event})}\n\n"
                seen_events += 1

        if final_state:
            for node_output in final_state.values():
                if isinstance(node_output, dict) and node_output.get("final_answer"):
                    answer = node_output["final_answer"]
                    sources = node_output.get("sources_used", [])
                    confidence = node_output.get("confidence_level", "MEDIUM")

                    words = answer.split()
                    for i, word in enumerate(words):
                        token = word + (" " if i < len(words) - 1 else "")
                        yield f"data: {json.dumps({'type': 'token', 'data': token})}\n\n"

                    yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
                    yield f"data: {json.dumps({'type': 'confidence', 'data': confidence})}\n\n"

                    user_msg = Message(
                        workspace_id=workspace_id,
                        session_id=UUID(session_id) if session_id else None,
                        user_id=UUID(user_id),
                        role="user",
                        content=query,
                    )
                    assistant_msg = Message(
                        workspace_id=workspace_id,
                        session_id=UUID(session_id) if session_id else None,
                        user_id=UUID(user_id),
                        role="assistant",
                        content=answer,
                        sources=sources,
                        confidence=confidence,
                    )
                    db.add(user_msg)
                    db.add(assistant_msg)
                    await db.commit()

                    # Generate title if this is the first exchange in a session
                    if session_id and len(memory.recent_turns) == 0:
                        try:
                            prompt = f"User: {query}\nAssistant: {answer}\n\nGenerate a short 3-5 word title for this chat."
                            system = "You are a helpful assistant. Output ONLY the short title, no quotes, no prefix."
                            title = await get_llm_response(prompt=prompt, system_prompt=system, max_tokens=15)
                            
                            if title:
                                title = title.strip(' "\'').strip()
                                session_record = await db.execute(select(Session).where(Session.id == UUID(session_id)))
                                session_record = session_record.scalar_one_or_none()
                                if session_record:
                                    session_record.title = title
                                    await db.commit()
                                    yield f"data: {json.dumps({'type': 'session_update', 'data': {'id': session_id, 'title': title}})}\n\n"
                        except Exception as e:
                            print(f"[chat] Title generation failed: {e}")

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
            session_id=str(payload.session_id) if payload.session_id else None,
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