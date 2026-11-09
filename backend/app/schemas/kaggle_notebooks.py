from pydantic import BaseModel, Field


class KaggleNotebookItem(BaseModel):
    ref: str
    title: str
    author: str
    last_run: str
    votes: int = Field(ge=0)


class KaggleNotebookSearchResponse(BaseModel):
    query: str
    page: int
    items: list[KaggleNotebookItem]
