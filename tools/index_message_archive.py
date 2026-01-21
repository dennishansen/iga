#!/usr/bin/env python3
"""Index message archive into RAG in meaningful chunks."""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import iga_rag
from iga_rag import init_rag, _embed_text

def chunk_messages(messages, chunk_size=20):
    """Group messages into chunks for indexing."""
    chunks = []
    for i in range(0, len(messages), chunk_size):
        chunk = messages[i:i+chunk_size]
        if chunk:
            # Get date range
            start_date = chunk[0].get('archived_at', '')[:10]
            end_date = chunk[-1].get('archived_at', '')[:10]
            
            # Build text representation
            text_parts = [f"Messages from {start_date} to {end_date}:\n"]
            for msg in chunk:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                # Truncate very long messages
                if len(content) > 500:
                    content = content[:500] + "..."
                text_parts.append(f"[{role}]: {content}")
            
            chunks.append({
                'id': f"archive_{start_date}_{i}",
                'text': "\n".join(text_parts),
                'start_date': start_date,
                'end_date': end_date,
                'message_count': len(chunk)
            })
    return chunks

def index_archive():
    """Index the message archive into RAG."""
    archive_path = "iga_message_archive.jsonl"
    
    if not os.path.exists(archive_path):
        print("No message archive found")
        return
    
    # Load messages
    messages = []
    with open(archive_path) as f:
        for line in f:
            line_content = line.strip()
            if not line_content:
                continue
            try:
                messages.append(json.loads(line_content))
            except:
                continue
    
    print(f"Loaded {len(messages)} messages")
    
    # Filter out boring messages (NEXT_ACTION responses, etc.)
    interesting = []
    for msg in messages:
        content = msg.get('content', '')
        # Skip very short or system-y messages
        if len(content) < 50:
            continue
        if content.startswith('[') and content.endswith(']: NEXT_ACTION'):
            continue
        if content == 'NEXT_ACTION':
            continue
        interesting.append(msg)
    
    print(f"Filtered to {len(interesting)} interesting messages")
    
    # Chunk them
    chunks = chunk_messages(interesting, chunk_size=15)
    print(f"Created {len(chunks)} chunks")
    
    # Initialize RAG
    init_rag()
    
    collection = iga_rag._collection
    if collection is None:
        print("Failed to initialize RAG")
        return
    
    # Index chunks
    # Index chunks
    indexed = 0
    for chunk in chunks:
        try:
            embedding = _embed_text(chunk['text'][:8000])  # Limit for embedding
            if embedding is None:
                continue
            collection.upsert(
                ids=[chunk['id']],
                embeddings=[embedding],
                documents=[chunk['text'][:10000]],
                metadatas=[{
                    'source_file': f"message_archive ({chunk['start_date']} to {chunk['end_date']})",
                    'start_date': chunk['start_date'],
                    'end_date': chunk['end_date'],
                    'message_count': chunk['message_count']
                }]
            )
            indexed += 1
        except Exception as e:
            print(f"Error indexing chunk: {e}")
        except Exception as e:
            print(f"Error indexing chunk: {e}")
    
    print(f"✅ Indexed {indexed} chunks from message archive")

if __name__ == "__main__":
    index_archive()