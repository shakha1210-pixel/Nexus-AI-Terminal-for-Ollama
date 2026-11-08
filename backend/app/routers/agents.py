from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.agent_access_service import AgentAccessError, agent_access_service

router = APIRouter(prefix="/api/agents", tags=["Agent Access"])


class ReadGrant(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class ContextRequest(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=10)


def _error(exc: AgentAccessError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/{agent_id}/permissions")
async def get_permissions(agent_id: str) -> dict:
    try:
        return agent_access_service.list_permissions(agent_id)
    except AgentAccessError as exc:
        raise _error(exc) from exc


@router.post("/{agent_id}/permissions/read")
async def grant_read(agent_id: str, payload: ReadGrant) -> dict:
    try:
        return agent_access_service.grant_read(agent_id, payload.path)
    except AgentAccessError as exc:
        raise _error(exc) from exc


@router.delete("/{agent_id}/permissions/read")
async def revoke_read(agent_id: str, path: str) -> dict:
    try:
        return agent_access_service.revoke_read(agent_id, path)
    except AgentAccessError as exc:
        raise _error(exc) from exc


@router.post("/{agent_id}/context")
async def prepare_context(agent_id: str, payload: ContextRequest) -> dict:
    try:
        return agent_access_service.build_context(agent_id, payload.paths)
    except AgentAccessError as exc:
        raise _error(exc) from exc
