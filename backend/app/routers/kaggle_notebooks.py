from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.schemas.kaggle_notebooks import KaggleNotebookSearchResponse
from app.services.kaggle_notebook_service import KaggleNotebookError, kaggle_notebook_service

router = APIRouter(prefix="/api/kaggle/notebooks", tags=["Kaggle Notebooks"])


@router.get("/search", response_model=KaggleNotebookSearchResponse)
async def search_notebooks(
    q: str = Query(min_length=2, max_length=120),
    page: int = Query(default=1, ge=1, le=100),
) -> dict:
    try:
        return await __import__("asyncio").to_thread(kaggle_notebook_service.search, q, page)
    except KaggleNotebookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{owner}/{slug}/download")
async def download_notebook(owner: str, slug: str) -> FileResponse:
    try:
        path = await __import__("asyncio").to_thread(
            kaggle_notebook_service.download, f"{owner}/{slug}"
        )
    except KaggleNotebookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type="application/x-ipynb+json",
        filename=path.name,
    )
