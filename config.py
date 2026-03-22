from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout: int = 120

    # ERP Database (read-only)
    erp_database_url: str = "sqlite:///D:/Projects/Umiya/Umiya_Dashboard/backend/db.sqlite3"

    # API Security
    ai_service_api_key: str = "umiya-ai-dev-key-change-in-production"

    # ChromaDB
    chroma_db_path: str = "./data/chroma_db"

    # Embedding Model
    embedding_model: str = "all-MiniLM-L6-v2"

    # Chat History
    chat_history_db_path: str = "./data/chat_history.db"

    # Service
    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "info"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()

# Ensure data directory exists
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
