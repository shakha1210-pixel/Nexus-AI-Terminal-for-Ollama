from typing import Literal

from pydantic import BaseModel, Field


class KaggleStartRequest(BaseModel):
    model: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._:/-]+$")


class ModeRequest(BaseModel):
    mode: Literal["local", "kaggle"]


class KaggleStatus(BaseModel):
    # idle | pushing | queued | starting | online | stopped | error
    state: str
    model: str | None = None
    kernel: str | None = None
    endpoint: str | None = None
    openai_base_url: str | None = None
    mode: str = "local"
    message: str
