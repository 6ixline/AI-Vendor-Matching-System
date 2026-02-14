"""Qdrant vector database operations"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Optional
import logging
import hashlib
from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantDB:
    
    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=30
        )
        
        # Get dimension from settings (handles both providers)
        if settings.EMBEDDING_PROVIDER == "openai":
            if "small" in settings.OPENAI_EMBEDDING_MODEL or "ada" in settings.OPENAI_EMBEDDING_MODEL:
                self.vector_size = 1536
            elif "large" in settings.OPENAI_EMBEDDING_MODEL:
                self.vector_size = 3072
            else:
                self.vector_size = 1536
        else:
            self.vector_size = settings.EMBEDDING_DIMENSION
        
        logger.info(f"Qdrant connected: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        logger.info(f"Vector dimension: {self.vector_size}")
    
    def _string_to_int_id(self, string_id: str) -> int:
        hash_value = int(hashlib.md5(string_id.encode()).hexdigest()[:8], 16)
        return abs(hash_value) % (2**31 - 1)
    
    def initialize_collections(self):
        collections = [
            settings.QDRANT_COLLECTION_VENDORS,
            settings.QDRANT_COLLECTION_TENDERS,
            settings.QDRANT_COLLECTION_FEEDBACK,
        ]
        
        for collection_name in collections:
            try:
                self.client.get_collection(collection_name)
                logger.info(f"Collection exists: {collection_name}")
            except Exception:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {collection_name}")
    
    def add_vendor(self, vendor_id: str, embedding: List[float], metadata: Dict):
        metadata["original_id"] = vendor_id
        
        point = PointStruct(
            id=self._string_to_int_id(vendor_id),
            vector=embedding,
            payload=metadata
        )
        
        self.client.upsert(
            collection_name=settings.QDRANT_COLLECTION_VENDORS,
            points=[point]
        )

    def add_tender(self, tender_id: str, embedding: List[float], metadata: Dict):
        metadata["original_id"] = tender_id

        int_id = self._string_to_int_id(tender_id)
        points = self.client.retrieve(
            collection_name=settings.QDRANT_COLLECTION_TENDERS,
            ids=[int_id]
        )
        
        if points:
            self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION_TENDERS,
                points=[PointStruct(
                    id=int_id,
                    vector=embedding,
                    payload=points[0].payload
                )]
            )
        else : 
            point = PointStruct(
                id=int_id,
                vector=embedding,
                payload=metadata
            )
            
            self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION_TENDERS,
                points=[point]
            )
    
    def add_vendors_batch(self, vendors_data: List[tuple]):
        points = []
        for vendor_id, embedding, metadata in vendors_data:
            metadata["original_id"] = vendor_id
            points.append(PointStruct(
                id=self._string_to_int_id(vendor_id),
                vector=embedding,
                payload=metadata
            ))
        
        self.client.upsert(
            collection_name=settings.QDRANT_COLLECTION_VENDORS,
            points=points
        )
        logger.info(f"Batch added {len(points)} vendors")
    
    def search_vendors(
        self, 
        query_vector: List[float], 
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        
        query_filter = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                if value:
                    must_conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
            if must_conditions:
                query_filter = Filter(must=must_conditions)
        
        results = self.client.search(
            collection_name=settings.QDRANT_COLLECTION_VENDORS,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter
        )
        
        return [
            {
                "id": hit.payload.get("original_id", str(hit.id)),
                "score": hit.score,
                "metadata": hit.payload
            }
            for hit in results
        ]
    
    def get_vendor(self, vendor_id: str) -> Optional[Dict]:
        try:
            points = self.client.retrieve(
                collection_name=settings.QDRANT_COLLECTION_VENDORS,
                ids=[self._string_to_int_id(vendor_id)]
            )
            return points[0].payload if points else None
        except Exception as e:
            logger.error(f"Error retrieving vendor {vendor_id}: {e}")
            return None
    
    def vendor_exists(self, vendor_id: str) -> bool:
        return self.get_vendor(vendor_id) is not None
    
    def update_vendor_embedding(self, vendor_id: str, new_embedding: List[float]):
        int_id = self._string_to_int_id(vendor_id)
        points = self.client.retrieve(
            collection_name=settings.QDRANT_COLLECTION_VENDORS,
            ids=[int_id]
        )
        
        if points:
            self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION_VENDORS,
                points=[PointStruct(
                    id=int_id,
                    vector=new_embedding,
                    payload=points[0].payload
                )]
            )
    
    def delete_vendor(self, vendor_id: str):
        self.client.delete(
            collection_name=settings.QDRANT_COLLECTION_VENDORS,
            points_selector=[self._string_to_int_id(vendor_id)]
        )
    
    def get_stats(self) -> Dict:
        try:
            vendors_info = self.client.get_collection(settings.QDRANT_COLLECTION_VENDORS)
            tenders_info = self.client.get_collection(settings.QDRANT_COLLECTION_TENDERS)
            
            return {
                "vendors_count": vendors_info.points_count,
                "tenders_count": tenders_info.points_count,
                "vector_dimension": self.vector_size,
                "status": "healthy",
                "embedding_provider": settings.EMBEDDING_PROVIDER
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"status": "error", "error": str(e)}
