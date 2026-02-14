"""Embedding generation service"""

from typing import List, Dict, Tuple
import logging
import numpy as np
import hashlib
import time
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    
    # Cache version - increment this when model changes
    CACHE_VERSION = "v1"
    
    # Cache TTL in seconds (24 hours)
    CACHE_TTL = 86400
    
    # Max cache size (entries)
    MAX_CACHE_SIZE = 10000
    
    # Batch size limit for OpenAI
    MAX_BATCH_SIZE = 100
    
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        
        # In-memory cache: {cache_key: (embedding, timestamp, version)}
        self._embedding_cache: Dict[str, Tuple[List[float], float, str]] = {}
        
        if self.provider == "openai":
            self._init_openai()
        else:
            self._init_sentence_transformer()
        
        # Include model name in cache version for uniqueness
        self._cache_version_key = f"{self.CACHE_VERSION}:{self.model_name}"
    
    def _init_openai(self):
        """Initialize OpenAI embeddings"""
        try:
            from openai import OpenAI
            
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in environment variables")
            
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model_name = settings.OPENAI_EMBEDDING_MODEL
            
            # OpenAI dimensions
            if "small" in self.model_name or "ada" in self.model_name:
                self.dimension = 1536
            elif "large" in self.model_name:
                self.dimension = 3072
            else:
                self.dimension = 1536
            
            logger.info(f"Initialized OpenAI embeddings: {self.model_name}, Dimension: {self.dimension}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            raise
    
    def _init_sentence_transformer(self):
        """Initialize Sentence Transformers (local)"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading Sentence Transformer: {settings.EMBEDDING_MODEL}")
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self.model_name = settings.EMBEDDING_MODEL
            self.dimension = self.model.get_sentence_embedding_dimension()
            
            logger.info(f"Model loaded. Dimension: {self.dimension}")
            
        except Exception as e:
            logger.error(f"Failed to load Sentence Transformer: {e}")
            raise
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        normalized = text.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Tuple[List[float], float, str]) -> bool:
        """Check if cache entry is still valid"""
        embedding, timestamp, version = cache_entry
        
        # Check version
        if version != self._cache_version_key:
            return False
        
        # Check TTL
        current_time = time.time()
        if current_time - timestamp > self.CACHE_TTL:
            return False
        
        return True
    
    def _evict_old_entries(self):
        """Evict expired or old entries if cache is too large"""
        if len(self._embedding_cache) <= self.MAX_CACHE_SIZE:
            return
        
        logger.info(f"Cache size {len(self._embedding_cache)} exceeds limit, evicting old entries")
        
        # Sort by timestamp (oldest first)
        sorted_items = sorted(
            self._embedding_cache.items(),
            key=lambda x: x[1][1]  # Sort by timestamp
        )
        
        # Keep only the newest MAX_CACHE_SIZE entries
        entries_to_keep = sorted_items[-self.MAX_CACHE_SIZE:]
        
        self._embedding_cache = dict(entries_to_keep)
        logger.info(f"Cache evicted, new size: {len(self._embedding_cache)}")
    
    def generate_vendor_embedding(self, vendor_data: Dict) -> List[float]:
        text = self._format_vendor_text(vendor_data)
        return self._generate_embedding(text)
    
    def generate_tender_embedding(self, tender_data: Dict) -> List[float]:
        text = self._format_tender_text(tender_data)
        return self._generate_embedding(text)
    
    def get_text_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string with caching
        
        Args:
            text: Plain text string to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        cache_key = self._get_cache_key(text)
        
        # Check cache first
        if cache_key in self._embedding_cache:
            cache_entry = self._embedding_cache[cache_key]
            
            if self._is_cache_valid(cache_entry):
                return cache_entry[0]  # Return embedding
            else:
                # Remove stale entry
                del self._embedding_cache[cache_key]
        
        # Generate and cache
        embedding = self._generate_embedding(text)
        current_time = time.time()
        self._embedding_cache[cache_key] = (embedding, current_time, self._cache_version_key)
        
        # Evict old entries if needed
        self._evict_old_entries()
        
        return embedding
    
    def get_text_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently
        Uses cache and batches uncached items
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors in same order as input
        """
        if not texts:
            return []
        
        # Deduplicate while preserving order
        unique_texts = []
        text_indices = {}
        
        for idx, text in enumerate(texts):
            normalized = text.strip().lower()
            if normalized not in text_indices:
                unique_texts.append(text)
                text_indices[normalized] = [idx]
            else:
                text_indices[normalized].append(idx)
        
        # Check cache and separate cached/uncached
        cached_results = {}
        uncached_texts = []
        uncached_indices = []
        
        for idx, text in enumerate(unique_texts):
            cache_key = self._get_cache_key(text)
            
            if cache_key in self._embedding_cache:
                cache_entry = self._embedding_cache[cache_key]
                
                if self._is_cache_valid(cache_entry):
                    cached_results[idx] = cache_entry[0]
                else:
                    # Remove stale entry
                    del self._embedding_cache[cache_key]
                    uncached_texts.append(text)
                    uncached_indices.append(idx)
            else:
                uncached_texts.append(text)
                uncached_indices.append(idx)
        
        # Batch generate uncached embeddings
        if uncached_texts:
            logger.info(f"Generating {len(uncached_texts)} new embeddings (from {len(texts)} total)")
            uncached_embeddings = self.generate_embeddings_batch(uncached_texts)
            
            current_time = time.time()
            
            # Cache the new embeddings
            for text, embedding in zip(uncached_texts, uncached_embeddings):
                cache_key = self._get_cache_key(text)
                self._embedding_cache[cache_key] = (embedding, current_time, self._cache_version_key)
            
            # Add to results
            for idx, embedding in zip(uncached_indices, uncached_embeddings):
                cached_results[idx] = embedding
            
            # Evict old entries if needed
            self._evict_old_entries()
        else:
            logger.info(f"All {len(texts)} embeddings found in cache")
        
        # Reconstruct results in original order
        result_embeddings = [None] * len(texts)
        for normalized, positions in text_indices.items():
            unique_idx = next(i for i, t in enumerate(unique_texts) 
                            if t.strip().lower() == normalized)
            embedding = cached_results[unique_idx]
            
            for pos in positions:
                result_embeddings[pos] = embedding
        
        return result_embeddings
    
    def _generate_embedding(self, text: str) -> List[float]:
        if self.provider == "openai":
            return self._generate_openai_embedding(text)
        else:
            return self._generate_local_embedding(text)
    
    def _generate_openai_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using OpenAI API with simple retry on rate limits
        
        Retries once if rate limit is hit, then fails
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model_name
            )
            return response.data[0].embedding
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a rate limit error
            if any(keyword in error_str for keyword in ['rate_limit', 'rate limit', '429', 'too many']):
                logger.warning("Rate limit hit on single embedding, waiting 2 seconds and retrying once...")
                time.sleep(2)
                
                # Retry once
                try:
                    response = self.client.embeddings.create(
                        input=text,
                        model=self.model_name
                    )
                    return response.data[0].embedding
                except Exception as retry_error:
                    logger.error(f"Retry failed after rate limit: {retry_error}")
                    raise
            
            # Not a rate limit error - fail immediately
            logger.error(f"OpenAI embedding error: {e}")
            raise
    
    def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding using local Sentence Transformer"""
        embedding = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return embedding.tolist()
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate multiple embeddings with batch size limits and rate limit handling
        
        For OpenAI: Splits large batches and retries on rate limits
        For local models: No limits needed
        """
        if self.provider == "openai":
            # Split large batches to avoid rate limits
            if len(texts) > self.MAX_BATCH_SIZE:
                logger.info(f"Splitting batch of {len(texts)} into chunks of {self.MAX_BATCH_SIZE}")
                
                all_embeddings = []
                for i in range(0, len(texts), self.MAX_BATCH_SIZE):
                    batch = texts[i:i + self.MAX_BATCH_SIZE]
                    
                    # Process batch with retry
                    batch_embeddings = self._generate_openai_batch(batch)
                    all_embeddings.extend(batch_embeddings)
                    
                    # Small delay between batches (only if more batches remaining)
                    if i + self.MAX_BATCH_SIZE < len(texts):
                        time.sleep(0.5)  # 500ms delay
                        logger.debug(f"Processed batch {i//self.MAX_BATCH_SIZE + 1}, waiting 0.5s before next batch")
                
                return all_embeddings
            
            # Normal batch (under limit)
            return self._generate_openai_batch(texts)
        
        else:
            # Local model - no rate limits
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings.tolist()
    
    def _generate_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Internal method for OpenAI batch generation with simple retry
        
        Retries once on rate limit, then fails
        """
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model_name
            )
            return [item.embedding for item in response.data]
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a rate limit error
            if any(keyword in error_str for keyword in ['rate_limit', 'rate limit', '429', 'too many']):
                logger.warning(f"Rate limit hit on batch of {len(texts)}, waiting 3 seconds and retrying once...")
                time.sleep(3)
                
                # Retry once
                try:
                    response = self.client.embeddings.create(
                        input=texts,
                        model=self.model_name
                    )
                    return [item.embedding for item in response.data]
                except Exception as retry_error:
                    logger.error(f"Batch retry failed after rate limit: {retry_error}")
                    raise
            
            # Not a rate limit error - fail immediately
            logger.error(f"OpenAI batch embedding error: {e}")
            raise
    
    def clear_cache(self):
        """Clear embedding cache"""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cache_size(self) -> int:
        """Get number of cached embeddings"""
        return len(self._embedding_cache)
    
    def get_cache_stats(self) -> Dict:
        """Get detailed cache statistics"""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        stale_version_entries = 0
        
        for cache_key, (embedding, timestamp, version) in self._embedding_cache.items():
            if version != self._cache_version_key:
                stale_version_entries += 1
            elif current_time - timestamp > self.CACHE_TTL:
                expired_entries += 1
            else:
                valid_entries += 1
        
        return {
            "total_entries": len(self._embedding_cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "stale_version_entries": stale_version_entries,
            "cache_version": self._cache_version_key,
            "max_cache_size": self.MAX_CACHE_SIZE,
            "max_batch_size": self.MAX_BATCH_SIZE,
            "cache_ttl_hours": self.CACHE_TTL / 3600
        }
    
    def _format_vendor_text(self, data: Dict) -> str:
        parts = [
            f"Company: {data.get('company_name', '')}",
            f"Description: {data.get('description', '')}",
            f"Industries: {', '.join(data.get('industries', []))}",
            f"Categories: {', '.join(data.get('categories', []))}",
            f"Products: {', '.join(data.get('products', []))}",
            f"Business Type: {data.get('business_type', '')}",
            f"Operating States: {', '.join(data.get('states', []))}",
            f"Certifications: {', '.join(data.get('certifications', []))}",
        ]
        
        if data.get('annual_turnover'):
            parts.append(f"Turnover: {data['annual_turnover']}")
        
        return " | ".join(filter(None, parts))
    
    def _format_tender_text(self, data: Dict) -> str:
        parts = [
            f"Title: {data.get('tender_title', '')}",
            f"Description: {data.get('brief_description', '')}",
            f"Industry: {data.get('industry', '')}",
            f"Categories: {', '.join(data.get('categories', []))}",
        ]
        
        if data.get('subcategory'):
            parts.append(f"Subcategory: {data['subcategory']}")
        
        products = data.get('products', [])
        if products:
            parts.append(f"Required Products: {', '.join(products)}")
        
        state_pref = data.get('state_preference', 'pan_india')
        if state_pref == 'pan_india':
            parts.append("Location: Pan India")
        else:
            states = data.get('states', [])
            if states:
                parts.append(f"States: {', '.join(states)}")
        
        parts.append(f"Required Certifications: {', '.join(data.get('required_certifications', []))}")
        
        if data.get('required_annual_turnover'):
            parts.append(f"Required Turnover: {data['required_annual_turnover']}")
        
        return " | ".join(filter(None, parts))
    
    def calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        vec1 = np.array(emb1)
        vec2 = np.array(emb2)
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return max(0.0, min(1.0, float(similarity)))
    
    def adjust_embedding_with_feedback(
        self,
        original: List[float],
        target: List[float],
        weight: float = 0.1
    ) -> List[float]:
        orig = np.array(original)
        targ = np.array(target)
        adjusted = orig + weight * (targ - orig)
        norm = np.linalg.norm(adjusted)
        if norm > 0:
            adjusted = adjusted / norm
        return adjusted.tolist()