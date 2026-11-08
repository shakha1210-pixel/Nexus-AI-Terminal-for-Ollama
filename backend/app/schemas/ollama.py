from pydantic import BaseModel


class OllamaStatus(BaseModel):
    connected: bool
    version: str | None = None
    message: str


class OllamaModel(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None
    digest: str | None = None
    family: str | None = None
    parameter_size: str | None = None
    quantization_level: str | None = None
