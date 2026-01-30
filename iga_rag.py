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
RAG_STATE_FILE = ".iga_chroma/rag_state.json"

# Global state
_client = None
_collection = None
_openai_client = None
_initialized = False

# Files to index - now discovered automatically
# Keeping this for any priority files that should always be indexed first
FILES_TO_INDEX = [
    "iga_memory.json",  # Memory is high priority
    "system_instructions.txt",  # Core identity
    "core/why_i_exist.md",  # Foundation
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


def _get_git_head():
    """Get current git HEAD commit hash."""
    import subprocess
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None


def _get_archive_line_count():
    """Get line count of message archive for change detection."""
    archive_path = "iga_message_archive.jsonl"
    try:
        if os.path.exists(archive_path):
            with open(archive_path, 'r') as f:
                return sum(1 for _ in f)
    except:
        pass
    return 0


def _load_rag_state():
    """Load saved RAG indexing state."""
    try:
        if os.path.exists(RAG_STATE_FILE):
            with open(RAG_STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}


def _save_rag_state(state):
    """Save RAG indexing state."""
    try:
        os.makedirs(os.path.dirname(RAG_STATE_FILE), exist_ok=True)
        with open(RAG_STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"RAG: Could not save state: {e}")


def needs_reindex():
    """Check if reindexing is needed based on git commit and archive size."""
    state = _load_rag_state()

    current_head = _get_git_head()
    current_archive_lines = _get_archive_line_count()

    saved_head = state.get('git_head')
    saved_archive_lines = state.get('archive_lines', 0)

    # Need reindex if git changed or archive grew significantly (10+ new messages)
    if current_head != saved_head:
        print(f"RAG: Git changed ({saved_head[:8] if saved_head else 'none'}... -> {current_head[:8] if current_head else 'none'}...)")
        return True

    if current_archive_lines - saved_archive_lines >= 10:
        print(f"RAG: Archive grew ({saved_archive_lines} -> {current_archive_lines} lines)")
        return True

    print(f"RAG: No changes detected, skipping reindex")
    return False


def mark_indexed():
    """Mark current state as indexed."""
    state = {
        'git_head': _get_git_head(),
        'archive_lines': _get_archive_line_count(),
        'indexed_at': datetime.now().isoformat()
    }
    _save_rag_state(state)


def _discover_all_files():
    """Find all indexable files (.py, .txt, .md) recursively."""
    all_files = []
    skip_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'chroma_db', '.chroma', 'sibling'}
    skip_files = {'console_log.txt'}  # Too noisy for RAG
    
    for root, dirs, files in os.walk('.'):
        # Skip hidden and build directories
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
        
        for fname in files:
            if fname in skip_files:
                continue
            if fname.endswith(('.py', '.txt', '.md', '.json')):
                path = os.path.join(root, fname)
                # Skip very large files and binary-ish json
                if os.path.getsize(path) < 100000:  # 100KB limit
                    all_files.append(path)
    
    return all_files


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
    files.extend(_discover_all_files())

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
    mark_indexed()
    return stats


def retrieve_context(query, top_k=10):
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
        seen_sources = set()  # For deduplication (using normalized paths)

        # Extract query terms for filename matching
        query_terms = set(query.lower().split())

        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else 0
                relevance = 1 - distance
                source = metadata.get("source_file", "unknown")

                # Normalize path to prevent duplicates (./file.md vs file.md)
                normalized_source = os.path.normpath(source)

                # Boost relevance for core/ files (foundational knowledge)
                if normalized_source.startswith("core/") or "/core/" in normalized_source:
                    relevance += 0.2

                # Boost relevance if query terms appear in filename
                filename = os.path.basename(normalized_source).lower()
                filename_no_ext = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
                if any(term in filename_no_ext for term in query_terms if len(term) > 2):
                    relevance += 0.1

                # Skip low relevance results (after boosts applied)
                if relevance < 0.25:
                    continue

                # Skip duplicate sources using normalized paths
                if normalized_source in seen_sources:
                    continue
                seen_sources.add(normalized_source)

                context_items.append({
                    "content": doc,
                    "source": normalized_source,
                    "relevance": relevance,
                })

        # Re-sort by relevance since boosts may have changed ordering
        context_items.sort(key=lambda x: x['relevance'], reverse=True)

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
