from fastapi import APIRouter
from models.schemas import HealthResponse
from services.ollama_client import ollama_client
from services.rag_service import rag_service
from database import check_db_connection
from config import settings

router = APIRouter(tags=["Health"])


@router.get("/health/", response_model=HealthResponse)
async def health_check():
    """Check the health of all AI service dependencies."""
    ollama_ok = await ollama_client.is_available()
    chromadb_ok = rag_service.is_available()
    db_ok = check_db_connection()

    all_ok = ollama_ok and chromadb_ok and db_ok
    status = "healthy" if all_ok else "degraded"

    return HealthResponse(
        status=status,
        ollama=ollama_ok,
        chromadb=chromadb_ok,
        erp_database=db_ok,
        model=settings.ollama_model,
    )
