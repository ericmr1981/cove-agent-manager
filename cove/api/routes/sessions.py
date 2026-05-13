from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cove.session_store.service import SessionStoreService

router = APIRouter()
store = SessionStoreService()


class CreateSessionRequest(BaseModel):
    project_key: str
    config: dict | None = None


class EmitEventRequest(BaseModel):
    kind: str
    data: dict
    parent_uuid: str | None = None
    agent_id: str | None = None


@router.post("/sessions")
async def create_session(body: CreateSessionRequest):
    return await store.create_session(body.project_key, body.config)


@router.get("/sessions")
async def list_sessions(project_key: str | None = None, limit: int = 50, offset: int = 0):
    return await store.list_sessions(project_key, limit, offset)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    result = await store.get_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.post("/sessions/{session_id}/events")
async def emit_event(session_id: str, body: EmitEventRequest):
    return await store.emit_event(
        session_id=session_id,
        kind=body.kind,
        data=body.data,
        parent_uuid=body.parent_uuid,
        agent_id=body.agent_id,
    )


@router.get("/sessions/{session_id}/events")
async def get_events(session_id: str, offset: int = 0, limit: int = 100):
    return await store.get_events(session_id, offset, limit)
