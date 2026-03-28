from pydantic import BaseModel, Field


class DocumentProcessRequest(BaseModel):
    file_path: str
    file_name: str
    file_type: str = Field(..., pattern="^(pdf|docx|xlsx|csv|txt)$")
    user_id: int = Field(..., gt=0)


class DocumentProcessResponse(BaseModel):
    document_id: str
    file_name: str
    summary: str
    entities: list[str]
    page_count: int
    indexed: bool
