import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from config import settings

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """SQLite-backed conversation history storage."""

    def __init__(self):
        self.db_path = settings.chat_history_db_path
        self._initialized = False

    def initialize(self):
        """Create tables if they don't exist."""
        if self._initialized:
            return
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT DEFAULT 'New Conversation',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_conversations_user
                    ON conversations(user_id);
            """)
            conn.commit()
            self._initialized = True
            logger.info("Chat history database initialized")
        finally:
            conn.close()

    def create_conversation(self, user_id: int, title: str = "New Conversation") -> str:
        """Create a new conversation and return its ID."""
        if not self._initialized:
            self.initialize()
        conversation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, user_id, title, now, now),
            )
            conn.commit()
            return conversation_id
        finally:
            conn.close()

    def add_message(self, conversation_id: str, role: str, content: str):
        """Add a message to a conversation."""
        if not self._initialized:
            self.initialize()
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_messages(self, conversation_id: str, limit: int = 50) -> list[dict]:
        """Get messages for a conversation."""
        if not self._initialized:
            self.initialize()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM messages "
                "WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_conversations(self, user_id: int) -> list[dict]:
        """List conversations for a user."""
        if not self._initialized:
            self.initialize()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT c.id as conversation_id, c.title, c.updated_at, "
                "(SELECT content FROM messages WHERE conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_message, "
                "(SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count "
                "FROM conversations c "
                "WHERE c.user_id = ? "
                "ORDER BY c.updated_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_conversation(self, conversation_id: str) -> dict | None:
        """Get a single conversation's details."""
        if not self._initialized:
            self.initialize()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT id as conversation_id, title, user_id, created_at, updated_at "
                "FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_title(self, conversation_id: str, title: str):
        """Update conversation title."""
        if not self._initialized:
            self.initialize()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (title, conversation_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and its messages."""
        if not self._initialized:
            self.initialize()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            result = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()


chat_history = ChatHistoryService()
