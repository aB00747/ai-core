from fastapi import APIRouter, Depends
from dependencies import verify_api_key
from models.schemas import DocumentProcessRequest, DocumentProcessResponse
from services.document_processor import document_processor

router = APIRouter(prefix="/documents", tags=["Documents"], dependencies=[Depends(verify_api_key)])


@router.post("/process/", response_model=DocumentProcessResponse)
async def process_document(request: DocumentProcessRequest):
    """Process and index a document."""
    result = await document_processor.process(
        file_path=request.file_path,
        file_name=request.file_name,
        file_type=request.file_type,
        user_id=request.user_id,
    )
    return DocumentProcessResponse(**result)
