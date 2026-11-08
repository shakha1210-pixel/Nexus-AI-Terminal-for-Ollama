from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.workspace_service import WorkspaceError, workspace_service

router = APIRouter(prefix="/api/workspace", tags=["Workspace"])


class FileWrite(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=2 * 1024 * 1024)


class DirectoryCreate(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class FileUpload(BaseModel):
    directory: str = Field(default="", max_length=500)
    filename: str = Field(min_length=1, max_length=255)
    data_base64: str = Field(min_length=1, max_length=14 * 1024 * 1024)


def _handle_workspace_error(exc: WorkspaceError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/tree")
async def get_tree(path: str = "") -> dict:
    try:
        return workspace_service.tree(path)
    except WorkspaceError as exc:
        raise _handle_workspace_error(exc) from exc


@router.get("/file")
async def get_file(path: str) -> dict:
    try:
        return workspace_service.read_file(path)
    except WorkspaceError as exc:
        raise _handle_workspace_error(exc) from exc


@router.put("/file")
async def put_file(payload: FileWrite) -> dict:
    try:
        return workspace_service.write_file(payload.path, payload.content)
    except WorkspaceError as exc:
        raise _handle_workspace_error(exc) from exc


@router.post("/directory")
async def post_directory(payload: DirectoryCreate) -> dict:
    try:
        return workspace_service.create_directory(payload.path)
    except WorkspaceError as exc:
        raise _handle_workspace_error(exc) from exc


@router.post("/upload")
async def post_upload(payload: FileUpload) -> dict:
    try:
        return workspace_service.save_upload(payload.directory, payload.filename, payload.data_base64)
    except WorkspaceError as exc:
        raise _handle_workspace_error(exc) from exc
