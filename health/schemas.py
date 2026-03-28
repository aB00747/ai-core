from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    ollama: bool
    chromadb: bool
    erp_database: bool
    model: str
    version: str = "1.0.0"
