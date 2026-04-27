import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from core import rag_service
from chat.history import chat_history

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

# CORS - allow Django backend and frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000",
                   "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from health import router as health_router
from chat import router as chat_router
from insights import router as insights_router
from documents import router as documents_router
from ocr.router import router as ocr_router

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(insights_router)
app.include_router(documents_router)
app.include_router(ocr_router)


@app.get("/")
async def root():
    return {"service": "Umiya AI Service", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
