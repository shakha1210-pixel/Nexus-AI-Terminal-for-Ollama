from fastapi import APIRouter, HTTPException, Query

from app.schemas.kaggle import KaggleNotebook, KagglePullResponse
from app.services.kaggle_service import KaggleServiceError, kaggle_service

router = APIRouter(prefix="/api/kaggle", tags=["Kaggle"])


def _raise_kaggle_error(exc: KaggleServiceError) -> None:
    message = str(exc)
    lowered = message.lower()
    status_code = 503 if "credentials" in lowered or "not installed" in lowered else 502
    raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/notebooks", response_model=list[KaggleNotebook])
async def list_notebooks(
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1, le=1000),
) -> list[KaggleNotebook]:
    try:
        return kaggle_service.list_notebooks(search=search, page=page)
    except KaggleServiceError as exc:
        _raise_kaggle_error(exc)


@router.post("/notebooks/{owner}/{slug}/pull", response_model=KagglePullResponse)
async def pull_notebook(owner: str, slug: str) -> KagglePullResponse:
    try:
        return KagglePullResponse(**kaggle_service.pull_notebook(f"{owner}/{slug}"))
    except KaggleServiceError as exc:
        _raise_kaggle_error(exc)
