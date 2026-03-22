import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from services.rag_service import rag_service
from services.chat_history import chat_history

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, cleanup on shutdown."""
    logger.info("Starting Umiya AI Service...")

    # Initialize chat history DB
    chat_history.initialize()
    logger.info("Chat history database ready")

    # Initialize RAG service (ChromaDB + embeddings)
    try:
        rag_service.initialize()
        logger.info("RAG service ready")
    except Exception as e:
        logger.warning(f"RAG service initialization failed (will retry on use): {e}")

    logger.info(f"AI Service started - Model: {settings.ollama_model}")
    yield
    logger.info("Shutting down Umiya AI Service...")


app = FastAPI(
    title="Umiya AI Service",
    description="AI-powered assistant for Umiya Chemical Trading ERP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow Django backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from routers.health import router as health_router
from routers.chat import router as chat_router
from routers.insights import router as insights_router
from routers.documents import router as documents_router

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(insights_router)
app.include_router(documents_router)


@app.get("/")
async def root():
    return {"service": "Umiya AI Service", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
