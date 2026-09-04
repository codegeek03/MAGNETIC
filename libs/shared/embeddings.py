"""
libs/shared/embeddings.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Wrapper for generating embeddings using Google's models.
"""

import os
from typing import List

from google import genai
from pydantic import BaseModel

from libs.shared.settings import get_settings


class EmbeddingResult(BaseModel):
    vector: List[float]
    model: str
    tokens: int = 0


class Embedder:
    """Generates embeddings using Google's text-embedding-004 model."""
    
    def __init__(self):
        settings = get_settings()
        api_key = os.getenv("GEMINI_API_KEY", settings.google_api_key)
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = "text-embedding-004"

    def embed_text(self, text: str) -> EmbeddingResult:
        """Embed a single piece of text."""
        if not self.client:
            # Fallback for environments without an API key (e.g. CI)
            return EmbeddingResult(vector=[0.0] * 768, model="fallback")

        # truncate text if it's too long for the embedding model (rough approximation)
        safe_text = text[:8000]
        
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=safe_text
        )
        
        # genai SDK returns embeddings in response.embeddings[0].values
        vector = response.embeddings[0].values
        
        return EmbeddingResult(
            vector=vector,
            model=self.model_name,
        )

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Embed multiple texts efficiently."""
        if not self.client:
            return [EmbeddingResult(vector=[0.0] * 768, model="fallback") for _ in texts]
            
        safe_texts = [text[:8000] for text in texts]
        
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=safe_texts
        )
        
        return [
            EmbeddingResult(vector=emb.values, model=self.model_name)
            for emb in response.embeddings
        ]
