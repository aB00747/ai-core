import logging
import uuid
import chromadb
from sentence_transformers import SentenceTransformer
from config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """ChromaDB + sentence-transformers for document retrieval."""

    def __init__(self):
        self._client = None
        self._collection = None
        self._embedder = None
        self._initialized = False

    def initialize(self):
        """Initialize ChromaDB and embedding model."""
        if self._initialized:
            return
        try:
            self._client = chromadb.PersistentClient(path=settings.chroma_db_path)
            self._collection = self._client.get_or_create_collection(
                name="umiya_documents",
                metadata={"hnsw:space": "cosine"},
            )
            self._embedder = SentenceTransformer(settings.embedding_model)
            self._initialized = True
            logger.info("RAG service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a text string."""
        if not self._initialized:
            self.initialize()
        return self._embedder.encode(text).tolist()

    def add_document(
        self,
        text: str,
        metadata: dict | None = None,
        doc_id: str | None = None,
    ) -> str:
        """Add a document to the vector store."""
        if not self._initialized:
            self.initialize()

        doc_id = doc_id or str(uuid.uuid4())
        embedding = self.embed_text(text)

        # Chunk long documents
        chunks = self._chunk_text(text, max_length=500, overlap=50)
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            ids.append(chunk_id)
            embeddings.append(self.embed_text(chunk))
            documents.append(chunk)
            chunk_meta = {**(metadata or {}), "parent_id": doc_id, "chunk_index": i}
            metadatas.append(chunk_meta)

        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Added document {doc_id} with {len(chunks)} chunks")
        return doc_id

    def search(self, query: str, n_results: int = 3) -> list[dict]:
        """Search for relevant documents."""
        if not self._initialized:
            self.initialize()

        query_embedding = self.embed_text(query)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        docs = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                docs.append({
                    "content": doc,
                    "metadata": meta,
                    "relevance": 1 - distance,  # cosine distance to similarity
                })
        return docs

    def is_available(self) -> bool:
        """Check if ChromaDB is operational."""
        try:
            if not self._initialized:
                self.initialize()
            self._client.heartbeat()
            return True
        except Exception:
            return False

    def get_document_count(self) -> int:
        """Get the total number of document chunks stored."""
        if not self._initialized:
            return 0
        return self._collection.count()

    @staticmethod
    def _chunk_text(text: str, max_length: int = 500, overlap: int = 50) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0

        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1

            if current_length >= max_length:
                chunks.append(" ".join(current_chunk))
                # Keep overlap words for context
                overlap_words = max(1, overlap // 5)
                current_chunk = current_chunk[-overlap_words:]
                current_length = sum(len(w) + 1 for w in current_chunk)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks


rag_service = RAGService()
