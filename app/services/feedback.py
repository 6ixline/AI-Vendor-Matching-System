"""Feedback processing for continuous improvement"""

import logging
from typing import Dict
from datetime import datetime
from app.schemas.matching import FeedbackInput
from app.db.qdrant import QdrantDB
from app.services.embedding import EmbeddingService
from app.core.config import settings

logger = logging.getLogger(__name__)


class FeedbackService:
    
    def __init__(self, db: QdrantDB, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service
    
    def process_feedback(self, feedback: FeedbackInput) -> Dict:
        logger.info(
            f"Processing feedback: tender={feedback.tender_id}, "
            f"vendor={feedback.vendor_id}, success={feedback.match_success}"
        )
        
        if not feedback.match_success or not feedback.selected:
            logger.info("Negative or unselected feedback - no embedding adjustment")
            return {
                "adjustment": "none",
                "reason": "negative_feedback_or_not_selected"
            }
        
        vendor_data = self.db.get_vendor(feedback.vendor_id)
        if not vendor_data:
            logger.warning(f"Vendor not found: {feedback.vendor_id}")
            return {"adjustment": "none", "reason": "vendor_not_found"}
        
        adjustment_weight = settings.FEEDBACK_ADJUSTMENT_WEIGHT
        if feedback.rating:
            adjustment_weight *= (feedback.rating / 5.0)
        
        try:
            vendor_embedding = self.embedding_service.generate_vendor_embedding(vendor_data)
            
            adjustment_signal = self._generate_adjustment_signal(feedback, vendor_data)
            target_embedding = self.embedding_service._generate_embedding(adjustment_signal)
            
            adjusted_embedding = self.embedding_service.adjust_embedding_with_feedback(
                original=vendor_embedding,
                target=target_embedding,
                weight=adjustment_weight
            )
            
            self.db.update_vendor_embedding(feedback.vendor_id, adjusted_embedding)
            
            logger.info(f"Updated embedding for vendor {feedback.vendor_id}")
            
            return {
                "adjustment": "applied",
                "vendor_id": feedback.vendor_id,
                "tender_id": feedback.tender_id,
                "weight": adjustment_weight,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return {"adjustment": "error", "error": str(e)}
    
    def _generate_adjustment_signal(self, feedback: FeedbackInput, vendor_data: Dict) -> str:
        signal_parts = [
            f"Successful match for: {vendor_data.get('company_name')}",
            f"Matched tender type: {feedback.tender_id}",
        ]
        
        if feedback.comments:
            signal_parts.append(f"Feedback: {feedback.comments}")
        
        if feedback.rating and feedback.rating >= 4:
            signal_parts.append("Highly rated match - strong positive signal")
        
        return " | ".join(signal_parts)
