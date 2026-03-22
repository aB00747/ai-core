"""Utility script to view ChromaDB contents."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from config import settings

client = chromadb.PersistentClient(path=settings.chroma_db_path)

print(f"ChromaDB path: {settings.chroma_db_path}")
print(f"Collections: {[c.name for c in client.list_collections()]}\n")

for col in client.list_collections():
    collection = client.get_collection(col.name)
    count = collection.count()
    print(f"Collection: {col.name}")
    print(f"  Documents: {count}")

    if count > 0:
        # Get all documents (limit 20)
        results = collection.get(limit=20, include=["documents", "metadatas"])
        print(f"  Showing first {min(count, 20)} entries:\n")
        for i, doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            text = results["documents"][i][:150] if results["documents"] else ""
            print(f"  [{i+1}] ID: {doc_id}")
            print(f"      Metadata: {meta}")
            print(f"      Preview: {text}...")
            print()
    else:
        print("  (empty - process documents via /documents/process/ to add data)\n")
