# RAG module for Iga - Retrieval Augmented Generation
# Uses ChromaDB for vector storage and OpenAI embeddings

import os
import json
import hashlib
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ChromaDB and OpenAI imports
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("Warning: chromadb not installed. RAG features disabled.")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai not installed. RAG features disabled.")

# Configuration
CHROMA_PERSIST_DIR = ".iga_chroma"
COLLECTION_NAME = "iga_knowledge"
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200  # overlap between chunks

# Global state
_client = None
_collection = None
_openai_client = None
_initialized = False

# Files to index (relative to project root)
FILES_TO_INDEX = [
    "iga_memory.json",
    "iga_journal.txt",
    # .md files will be discovered dynamically
]

# Directories to scan for .md files
MD_DIRECTORIES = [
    ".",
    "letters",
    "notes",
    "creative",
    "moments",
    "docs",
    "research",
    "journal",
    "artifacts",
]


def _get_openai_client():
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _embed_text(text):
    """Generate embedding for text using OpenAI."""
    if not OPENAI_AVAILABLE:
        return None
    try:
        client = _get_openai_client()
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def _chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if end >= len(text):
            break
    return chunks


def _content_hash(content):
    """Generate hash of content for change detection."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def _discover_md_files():
    """Find all .md files in configured directories."""
    md_files = []
    for directory in MD_DIRECTORIES:
        if os.path.exists(directory):
            for item in os.listdir(directory):
                if item.endswith('.md'):
                    path = os.path.join(directory, item)
                    if os.path.isfile(path):
                        md_files.append(path)
    return md_files


def init_rag():
    """Initialize ChromaDB with persistent storage."""
    global _client, _collection, _initialized

    if not CHROMADB_AVAILABLE or not OPENAI_AVAILABLE:
        print("RAG: Missing dependencies (chromadb or openai)")
        return False

    try:
        # Create persistent directory
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

        # Initialize ChromaDB with persistence
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

        # Get or create collection with OpenAI embedding function
        # We'll use our own embedding function for more control
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        _initialized = True
        print(f"RAG: Initialized (collection has {_collection.count()} documents)")
        return True

    except Exception as e:
        print(f"RAG init error: {e}")
        _initialized = False
        return False


def index_files(force_reindex=False):
    """Index Iga's files into ChromaDB."""
    global _collection

    if not _initialized or _collection is None:
        print("RAG: Not initialized, call init_rag() first")
        return {"indexed": 0, "skipped": 0, "errors": []}

    stats = {"indexed": 0, "skipped": 0, "errors": []}

    # Build list of files to index
    files = FILES_TO_INDEX.copy()
    files.extend(_discover_md_files())

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for f in files:
        normalized = os.path.normpath(f)
        if normalized not in seen:
            seen.add(normalized)
            unique_files.append(f)

    for filepath in unique_files:
        if not os.path.exists(filepath):
            continue

        try:
            # Read file content
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if not content.strip():
                continue

            # Check if file has changed since last index
            content_hash = _content_hash(content)
            file_id_base = filepath.replace('/', '_').replace('.', '_')

            # For JSON files, extract meaningful content
            if filepath.endswith('.json'):
                try:
                    data = json.loads(content)
                    # For iga_memory.json, extract memory entries
                    if isinstance(data, dict):
                        lines = []
                        for key, value in data.items():
                            if isinstance(value, dict) and 'value' in value:
                                lines.append(f"[{key}]: {value['value']}")
                            else:
                                lines.append(f"[{key}]: {json.dumps(value)}")
                        content = "\n".join(lines)
                except json.JSONDecodeError:
                    pass  # Use raw content

            # Check existing documents for this file
            existing = _collection.get(
                where={"source_file": filepath},
                include=["metadatas"]
            )

            # Skip if content hasn't changed
            if existing['ids'] and not force_reindex:
                existing_hash = existing['metadatas'][0].get('content_hash') if existing['metadatas'] else None
                if existing_hash == content_hash:
                    stats["skipped"] += 1
                    continue
                else:
                    # Delete old chunks before re-indexing
                    _collection.delete(ids=existing['ids'])

            # Chunk the content
            chunks = _chunk_text(content)

            # Index each chunk
            for i, chunk in enumerate(chunks):
                doc_id = f"{file_id_base}_chunk_{i}"

                # Generate embedding
                embedding = _embed_text(chunk)
                if embedding is None:
                    continue

                # Add to collection
                _collection.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{
                        "source_file": filepath,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "content_hash": content_hash,
                        "indexed_at": datetime.now().isoformat()
                    }]
                )

            stats["indexed"] += 1
            print(f"RAG: Indexed {filepath} ({len(chunks)} chunks)")

        except Exception as e:
            stats["errors"].append(f"{filepath}: {e}")
            print(f"RAG: Error indexing {filepath}: {e}")

    print(f"RAG: Indexing complete - {stats['indexed']} indexed, {stats['skipped']} skipped, {len(stats['errors'])} errors")
    return stats


def retrieve_context(query, top_k=5):
    """Find relevant chunks for a query."""
    if not _initialized or _collection is None:
        return []

    if _collection.count() == 0:
        return []

    try:
        # Generate query embedding
        query_embedding = _embed_text(query)
        if query_embedding is None:
            return []

        # Query the collection
        results = _collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, _collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        context_items = []
        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else 0

                context_items.append({
                    "content": doc,
                    "source": metadata.get("source_file", "unknown"),
                    "relevance": 1 - distance,  # Convert distance to similarity
                })

        return context_items

    except Exception as e:
        print(f"RAG retrieve error: {e}")
        return []


def format_context_for_prompt(context_items):
    """Format retrieved context for injection into system prompt."""
    if not context_items:
        return ""

    lines = ["[RELEVANT CONTEXT FROM YOUR KNOWLEDGE]:"]
    for item in context_items:
        source = item.get("source", "unknown")
        content = item.get("content", "")[:500]  # Truncate long chunks
        relevance = item.get("relevance", 0)
        lines.append(f"--- From {source} (relevance: {relevance:.2f}) ---")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def get_rag_status():
    """Get current RAG system status."""
    return {
        "initialized": _initialized,
        "chromadb_available": CHROMADB_AVAILABLE,
        "openai_available": OPENAI_AVAILABLE,
        "document_count": _collection.count() if _collection else 0,
        "persist_dir": CHROMA_PERSIST_DIR,
    }


# For standalone testing
if __name__ == "__main__":
    print("Testing RAG module...")

    if init_rag():
        print("\nIndexing files...")
        stats = index_files()
        print(f"Stats: {stats}")

        print("\nTesting retrieval...")
        results = retrieve_context("What have I learned about consciousness?")
        for r in results:
            print(f"\n[{r['source']}] (relevance: {r['relevance']:.2f})")
            print(r['content'][:200] + "...")
    else:
        print("Failed to initialize RAG")
