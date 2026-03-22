"""Utility script to view chat history from SQLite."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from config import settings

db_path = settings.chat_history_db_path
print(f"Chat history DB: {db_path}\n")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# List all conversations
conversations = conn.execute(
    "SELECT id, user_id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
).fetchall()

print(f"Total conversations: {len(conversations)}\n")

for conv in conversations:
    print(f"{'='*60}")
    print(f"Conversation: {conv['id']}")
    print(f"Title: {conv['title']}")
    print(f"User ID: {conv['user_id']}")
    print(f"Created: {conv['created_at']}")
    print(f"Updated: {conv['updated_at']}")

    messages = conn.execute(
        "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conv['id'],),
    ).fetchall()

    print(f"Messages: {len(messages)}\n")
    for msg in messages:
        role = msg['role'].upper()
        content = msg['content']
        print(f"  [{role}] {content[:200]}{'...' if len(content) > 200 else ''}")
        print()

conn.close()
