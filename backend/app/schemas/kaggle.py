from pydantic import BaseModel, HttpUrl


class KaggleNotebook(BaseModel):
    ref: str
    title: str
    language: str | None = None
    votes: int = 0
    last_updated: str | None = None
    url: HttpUrl
    is_pulled: bool = False


class KagglePullResponse(BaseModel):
    ref: str
    filename: str
    status: str
