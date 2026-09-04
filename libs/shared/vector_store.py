"""
libs/shared/vector_store.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
PostgreSQL pgvector integration for RAG semantic search.
"""

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg
from pgvector.psycopg import register_vector

from libs.shared.embeddings import Embedder

logger = logging.getLogger(__name__)


class VectorStore:
    """Provides semantic search capabilities over pgvector."""
    
    def __init__(self):
        db_url = os.getenv("DATABASE_URL")
        # Ensure we use psycopg-compatible connection string
        self.db_url = db_url.replace("postgresql+psycopg://", "postgresql://") if db_url else None
        self.embedder = Embedder()

    @contextmanager
    def _get_conn(self):
        if not self.db_url:
            yield None
            return
            
        with psycopg.connect(self.db_url) as conn:
            register_vector(conn)
            yield conn

    def store_document(
        self,
        source: str,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Embed and store a document in the vector database."""
        if not self.db_url:
            logger.warning("VectorStore disabled (no DATABASE_URL)")
            return False
            
        try:
            embedding = self.embedder.embed_text(text)
            
            with self._get_conn() as conn:
                if not conn:
                    return False
                    
                conn.execute(
                    """
                    INSERT INTO knowledge_embeddings 
                    (source, document_id, chunk_text, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        source,
                        document_id,
                        text,
                        embedding.vector,
                        json.dumps(metadata or {})
                    )
                )
            return True
        except Exception as exc:
            logger.error("Failed to store document in VectorStore: %s", exc)
            return False

    def similarity_search(self, query: str, top_k: int = 3, min_similarity: float = 0.5) -> List[Dict[str, Any]]:
        """Search for semantically similar documents."""
        if not self.db_url:
            return []
            
        try:
            embedding = self.embedder.embed_text(query)
            
            # Using vector_cosine_ops (<=>) for cosine distance
            # Similarity = 1 - Cosine Distance
            query_sql = """
                SELECT source, chunk_text, metadata, 1 - (embedding <=> %s::vector) AS similarity
                FROM knowledge_embeddings
                WHERE 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            
            results = []
            with self._get_conn() as conn:
                if not conn:
                    return []
                    
                cursor = conn.execute(
                    query_sql,
                    (embedding.vector, embedding.vector, min_similarity, embedding.vector, top_k)
                )
                
                for row in cursor.fetchall():
                    results.append({
                        "source": row[0],
                        "text": row[1],
                        "metadata": row[2],
                        "similarity": float(row[3])
                    })
                    
            return results
        except Exception as exc:
            logger.error("Similarity search failed: %s", exc)
            return []
