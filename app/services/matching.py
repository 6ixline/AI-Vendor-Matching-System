"""Core matching logic"""

from typing import List, Dict, Optional, Set
import logging
import time
import numpy as np
from app.schemas.vendor import Vendor
from app.schemas.tender import Tender
from app.schemas.matching import MatchResult, MatchResponse
from app.db.qdrant import QdrantDB
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__) 

class MatchingService:
    
    def __init__(self, db: QdrantDB, embedding_service: EmbeddingService,  similarity_threshold: float = 0.2):
        self.db = db
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.turnover_hierarchy = [
            "0-1 Crore",
            "1-5 Crores",
            "5-10 Crores",
            "10-25 Crores",
            "25-50 Crores",
            "50-100 Crores",
            "100+ Crores"
        ]
    
    def add_vendor(self, vendor: Vendor) -> Dict:
        vendor_dict = vendor.model_dump()
        embedding = self.embedding_service.generate_vendor_embedding(vendor_dict)
        self.db.add_vendor(vendor.vendor_id, embedding, vendor_dict)
        logger.info(f"Added vendor: {vendor.vendor_id}")
        return {"status": "success", "vendor_id": vendor.vendor_id}

    def add_tender(self, tender: Tender) -> Dict:
        vendor_dict = tender.model_dump()
        embedding = self.embedding_service.generate_vendor_embedding(vendor_dict)
        self.db.add_tender(tender.tender_id, embedding, vendor_dict)
        logger.info(f"Added Tender: {tender.tender_id}")
        return {"status": "success", "tender_id": tender.tender_id}
    
    def sync_vendors_batch(self, vendors: List[Dict], force_update: bool = False) -> Dict:
        synced = 0
        updated = 0
        failed = 0
        errors = []
        
        batch_data = []
        
        for vendor_data in vendors:
            try:
                vendor_id = vendor_data.get("vendor_id")
                if not vendor_id:
                    failed += 1
                    errors.append(f"Missing vendor_id in {vendor_data.get('company_name')}")
                    continue
                
                if not force_update and self.db.vendor_exists(vendor_id):
                    updated += 1
                    continue
                
                embedding = self.embedding_service.generate_vendor_embedding(vendor_data)
                batch_data.append((vendor_id, embedding, vendor_data))
                synced += 1
                
            except Exception as e:
                failed += 1
                errors.append(f"Error processing {vendor_data.get('company_name')}: {str(e)}")
                logger.error(f"Vendor sync error: {e}")
        
        if batch_data:
            try:
                self.db.add_vendors_batch(batch_data)
            except Exception as e:
                logger.error(f"Batch insert failed: {e}")
                failed += len(batch_data)
                errors.append(f"Batch insert failed: {str(e)}")
        
        logger.info(f"Sync complete: {synced} synced, {updated} skipped, {failed} failed")
        
        return {
            "synced": synced,
            "updated": updated,
            "failed": failed,
            "errors": errors
        }
    
    def find_matching_vendors(
        self, 
        tender: Tender, 
        top_k: int = 5
    ) -> MatchResponse:
        start_time = time.time()
        
        tender_dict = tender.model_dump()
        tender_embedding = self.embedding_service.generate_tender_embedding(tender_dict)
        self.add_tender(tender)
        
        filters = self._build_filters(tender_dict)
        
        search_limit = min(top_k * 3, 50)
        results = self.db.search_vendors(
            query_vector=tender_embedding,
            top_k=search_limit,
            filters=filters
        )
        
        matches = []
        for rank, result in enumerate(results, 1):
            metadata = result["metadata"]

            if result["score"] < self.similarity_threshold:
                logger.debug(f"Vendor {result['id']} filtered out: score {result['score']:.3f} < threshold {self.similarity_threshold}")
                continue
            
            if not self._meets_hard_requirements(tender_dict, metadata):
                continue
            
            match_reasons = self._generate_match_reasons(tender_dict, metadata)
            match_score = self._calculate_match_score(
                tender_dict, 
                metadata, 
                result["score"]
            )
            
            matches.append(MatchResult(
                vendor_id=result["id"],
                company_name=metadata.get("company_name", "Unknown"),
                match_score=match_score,
                match_percentage=int(match_score * 100),
                match_reasons=match_reasons,
                vendor_details={
                    "company_name": metadata.get("company_name"),
                    "industries": metadata.get("industries", []),
                    "categories": metadata.get("categories", []),
                    "states": metadata.get("states", []),
                    "business_type": metadata.get("business_type"),
                    "annual_turnover": metadata.get("annual_turnover"),
                    "certifications": metadata.get("certifications", []),
                    "products": metadata.get("products", []),
                    "description": metadata.get("description", "")
                },
                ranking=rank
            ))
            
            if len(matches) >= top_k:
                break
        
        matches.sort(key=lambda x: x.match_score, reverse=True)
        
        for idx, match in enumerate(matches, 1):
            match.ranking = idx
        
        search_time = (time.time() - start_time) * 1000
        
        return MatchResponse(
            tender_id=tender.tender_id,
            total_matches=len(matches),
            matches=matches,
            search_time_ms=round(search_time, 2)
        )
    
    def _build_filters(self, tender_data: Dict) -> Dict:
        """Build filters based on tender requirements"""
        filters = {}
        return filters
    
    def _meets_hard_requirements(self, tender_data: Dict, vendor_data: Dict) -> bool:
        """Check if vendor meets mandatory requirements"""
        # 1. Check state availability
        state_pref = tender_data.get("state_preference", "pan_india")
        # if state_pref == "specific_states":
        #     tender_states = set(tender_data.get("states", []))
        #     vendor_states = set(vendor_data.get("states", []))
            
        #     if tender_states and not (tender_states & vendor_states):
        #         return False
        
        # 2. Check turnover requirement
        required_turnover = tender_data.get("required_annual_turnover")
        if required_turnover:
            if not self._meets_turnover_requirement(
                required_turnover, 
                vendor_data.get("annual_turnover")
            ):
                return False
        
        return True
    
    def _generate_match_reasons(self, tender_data: Dict, vendor_data: Dict) -> List[str]:
        """Generate detailed, prioritized match reasons using semantic similarity"""
        reasons = []
        
        # 1. Certifications
        cert_reason = self._get_certification_reason(tender_data, vendor_data)
        if cert_reason:
            reasons.append(cert_reason)
        
        # 2. Products (OPTIMIZED)
        product_reasons = self._get_product_match_reasons_semantic(tender_data, vendor_data)
        reasons.extend(product_reasons)
        
        # 3. Categories
        category_reason = self._get_category_match_reason(tender_data, vendor_data)
        if category_reason:
            reasons.append(category_reason)
        
        # 4. Industry (OPTIMIZED)
        industry_reason = self._get_industry_match_reason_semantic(tender_data, vendor_data)
        if industry_reason:
            reasons.append(industry_reason)
        
        # 5. Geography
        geo_reason = self._get_geographic_match_reason(tender_data, vendor_data)
        if geo_reason:
            reasons.append(geo_reason)
        
        # 6. Business capacity
        capacity_reasons = self._get_capacity_match_reasons(tender_data, vendor_data)
        reasons.extend(capacity_reasons)
        
        # 7. Expertise (OPTIMIZED)
        expertise_reason = self._get_expertise_match_reason_semantic(tender_data, vendor_data)
        if expertise_reason:
            reasons.append(expertise_reason)
        
        if not reasons:
            reasons.append("Relevant business profile for this requirement")
        
        return reasons[:6]

    def _get_certification_reason(self, tender_data: Dict, vendor_data: Dict) -> Optional[str]:
        """Generate certification match reason"""
        tender_certs = set(tender_data.get("required_certifications", []) or [])
        vendor_certs = set(vendor_data.get("certifications", []) or [])
        
        if not tender_certs:
            return None
        
        matching_certs = tender_certs & vendor_certs
        
        if not matching_certs:
            return None
        
        if len(matching_certs) == len(tender_certs):
            return f"Fully certified: {', '.join(sorted(matching_certs))}"
        else:
            return f"Has certifications: {', '.join(sorted(matching_certs))}"

    def _get_product_match_reasons_semantic(self, tender_data: Dict, vendor_data: Dict) -> List[str]:
        """
        OPTIMIZED: Generate product match reasons using BATCH semantic similarity
        Reduces API calls from N*M to 2 (one batch for tender, one batch for vendor)
        """
        reasons = []
        
        vendor_products = vendor_data.get("products", []) or []
        if not vendor_products:
            return reasons
        
        vendor_products = vendor_products[:20]
        
        tender_products = tender_data.get("products", []) or []
        tender_title = (tender_data.get("tender_title") or "").strip()
        tender_desc = (tender_data.get("brief_description") or "").strip()
        tender_text = f"{tender_title}. {tender_desc}"
        
        if not tender_products and (not tender_text or len(tender_text) < 10):
            return reasons
        
        try:
            # BATCH EMBED: All vendor products at once
            vendor_products_filtered = [vp for vp in vendor_products if vp and len(vp.strip()) >= 3]
            if not vendor_products_filtered:
                return reasons
            
            vendor_embeddings = self.embedding_service.get_text_embeddings_batch(vendor_products_filtered)
            
            explicit_matches = []
            implicit_matches = []
            
            # Check against explicit tender products
            if tender_products:
                # BATCH EMBED: All tender products at once
                tender_products_filtered = [tp for tp in tender_products if tp and len(tp.strip()) >= 3]
                tender_embeddings = self.embedding_service.get_text_embeddings_batch(tender_products_filtered)
                
                # Create similarity matrix
                for vendor_product, vendor_emb in zip(vendor_products_filtered, vendor_embeddings):
                    best_explicit_similarity = 0.0
                    best_explicit_match = None
                    
                    for tender_product, tender_emb in zip(tender_products_filtered, tender_embeddings):
                        # Exact match check
                        if (vendor_product.lower().strip() == tender_product.lower().strip() or
                            vendor_product.lower() in tender_product.lower() or
                            tender_product.lower() in vendor_product.lower()):
                            explicit_matches.append((vendor_product, 1.0))
                            best_explicit_match = True
                            break
                        
                        # Semantic similarity (already have embeddings)
                        similarity = self._cosine_similarity(vendor_emb, tender_emb)
                        
                        if similarity > best_explicit_similarity:
                            best_explicit_similarity = similarity
                            best_explicit_match = tender_product
                    
                    if best_explicit_match and not any(p[0] == vendor_product for p in explicit_matches):
                        if best_explicit_similarity >= 0.55:
                            explicit_matches.append((vendor_product, best_explicit_similarity))
                            continue
            
            # Check against tender description
            if not explicit_matches and tender_text and len(tender_text) >= 10:
                tender_text_embedding = self.embedding_service.get_text_embedding(tender_text)
                
                for vendor_product, vendor_emb in zip(vendor_products_filtered, vendor_embeddings):
                    similarity = self._cosine_similarity(vendor_emb, tender_text_embedding)
                    
                    if similarity >= 0.60:
                        implicit_matches.append((vendor_product, similarity))
            
            # Sort by similarity
            explicit_matches.sort(key=lambda x: x[1], reverse=True)
            implicit_matches.sort(key=lambda x: x[1], reverse=True)
            
            # Build reasons
            if explicit_matches:
                top_products = [p for p, _ in explicit_matches[:3]]
                
                if len(explicit_matches) == 1:
                    reasons.append(f"Supplies required product/service: {top_products[0]}")
                elif len(explicit_matches) == 2:
                    reasons.append(f"Supplies {top_products[0]} and {top_products[1]}")
                else:
                    remaining = len(explicit_matches) - 2
                    reasons.append(f"Supplies {top_products[0]}, {top_products[1]}, and {remaining} more required products")
            
            elif implicit_matches:
                top_products = [p for p, _ in implicit_matches[:3]]
                
                if len(top_products) == 1:
                    reasons.append(f"Supplies {top_products[0]}")
                elif len(top_products) == 2:
                    reasons.append(f"Supplies {top_products[0]} and {top_products[1]}")
                else:
                    remaining = len(implicit_matches) - 2
                    reasons.append(f"Supplies {top_products[0]}, {top_products[1]}, and {remaining} more relevant products")
        
        except Exception as e:
            logger.warning(f"Semantic product matching failed: {e}, falling back to keywords")
            return self._get_product_match_reasons_fallback(tender_data, vendor_data)
        
        return reasons

    def _get_product_match_reasons_fallback(self, tender_data: Dict, vendor_data: Dict) -> List[str]:
        """Fallback keyword-based product matching"""
        reasons = []
        
        vendor_products = vendor_data.get("products", []) or []
        tender_products = tender_data.get("products", []) or []
        tender_title = (tender_data.get("tender_title") or "").lower()
        tender_desc = (tender_data.get("brief_description") or "").lower()
        tender_combined = f"{tender_title} {tender_desc}".strip()
        
        if not vendor_products:
            return reasons
        
        explicit_product_keywords = set()
        for tp in tender_products:
            if tp:
                explicit_product_keywords.update(self._extract_keywords(tp.lower()))
        
        tender_keywords = set()
        if tender_combined:
            tender_keywords.update(self._extract_keywords(tender_combined))
        
        matched_products_explicit = []
        matched_products_implicit = []
        
        for vendor_product in vendor_products:
            if not vendor_product:
                continue
            
            vendor_product_lower = vendor_product.lower()
            
            # Check against explicit tender products
            if explicit_product_keywords:
                for tender_product in tender_products:
                    if not tender_product:
                        continue
                    
                    tender_product_lower = tender_product.lower()
                    
                    if tender_product_lower in vendor_product_lower or vendor_product_lower in tender_product_lower:
                        matched_products_explicit.append((vendor_product, 4))
                        break
                    
                    vendor_words = set(vendor_product_lower.split())
                    tender_product_words = set(tender_product_lower.split())
                    overlap = vendor_words & tender_product_words
                    
                    if overlap and len(overlap) >= 2:
                        matched_products_explicit.append((vendor_product, 3))
                        break
                    elif overlap:
                        matched_products_explicit.append((vendor_product, 2))
                        break
            
            # Check against tender text
            if not any(p[0] == vendor_product for p in matched_products_explicit):
                if tender_combined and vendor_product_lower in tender_combined:
                    matched_products_implicit.append((vendor_product, 3))
                else:
                    product_words = set(vendor_product_lower.split())
                    overlap = product_words & tender_keywords
                    
                    if overlap and len(overlap) >= 2:
                        matched_products_implicit.append((vendor_product, 2))
                    elif overlap:
                        matched_products_implicit.append((vendor_product, 1))
        
        matched_products_explicit.sort(key=lambda x: x[1], reverse=True)
        matched_products_implicit.sort(key=lambda x: x[1], reverse=True)
        
        # Build reasons
        if matched_products_explicit:
            top_products = [p[0] for p in matched_products_explicit[:3]]
            
            if len(matched_products_explicit) == 1:
                reasons.append(f"Supplies required product: {top_products[0]}")
            elif len(matched_products_explicit) == 2:
                reasons.append(f"Supplies {top_products[0]} and {top_products[1]}")
            else:
                remaining = len(matched_products_explicit) - 2
                reasons.append(f"Supplies {top_products[0]}, {top_products[1]}, and {remaining} more required products")
        
        elif matched_products_implicit:
            top_products = [p[0] for p in matched_products_implicit[:3]]
            
            if len(top_products) == 1:
                reasons.append(f"Supplies {top_products[0]}")
            elif len(top_products) == 2:
                reasons.append(f"Supplies {top_products[0]} and {top_products[1]}")
            else:
                remaining = len(matched_products_implicit) - 2
                reasons.append(f"Supplies {top_products[0]}, {top_products[1]}, and {remaining} more relevant products")
        
        return reasons

    def _product_match_multiplier(self, tender_data: Dict, vendor_data: Dict) -> float:
        """OPTIMIZED: Product match multiplier using batch embeddings"""
        tender_products = set(tender_data.get("products", []) or [])
        
        if not tender_products:
            return 1.0
        
        vendor_products = vendor_data.get("products", []) or []
        if not vendor_products:
            return 0.85
        
        try:
            tender_products_list = [tp for tp in tender_products if tp and len(tp.strip()) >= 3]
            vendor_products_list = [vp for vp in vendor_products[:20] if vp and len(vp.strip()) >= 3]
            
            if not tender_products_list or not vendor_products_list:
                return 0.85
            
            # BATCH EMBED: Both tender and vendor products
            tender_embeddings = self.embedding_service.get_text_embeddings_batch(tender_products_list)
            vendor_embeddings = self.embedding_service.get_text_embeddings_batch(vendor_products_list)
            
            matches = 0
            
            for tender_product, tender_emb in zip(tender_products_list, tender_embeddings):
                best_similarity = 0.0
                
                for vendor_product, vendor_emb in zip(vendor_products_list, vendor_embeddings):
                    if (tender_product.lower() in vendor_product.lower() or 
                        vendor_product.lower() in tender_product.lower()):
                        matches += 1
                        break
                    
                    similarity = self._cosine_similarity(tender_emb, vendor_emb)
                    if similarity > best_similarity:
                        best_similarity = similarity
                
                if best_similarity >= 0.60:
                    matches += 1
            
            if matches == 0:
                return 0.85
            
            match_ratio = matches / len(tender_products_list)
            
            if match_ratio >= 0.9:
                return 1.30
            elif match_ratio >= 0.7:
                return 1.20
            elif match_ratio >= 0.5:
                return 1.10
            else:
                return 1.0 + (0.10 * match_ratio)
        
        except Exception as e:
            logger.warning(f"Product multiplier calculation failed: {e}")
            return 1.0

    def _get_category_match_reason(self, tender_data: Dict, vendor_data: Dict) -> Optional[str]:
        """Generate category match reason"""
        tender_categories = set(tender_data.get("categories", []) or [])
        vendor_categories = set(vendor_data.get("categories", []) or [])
        matching_categories = tender_categories & vendor_categories
        
        if not matching_categories:
            return None
        
        match_count = len(matching_categories)
        total_required = len(tender_categories)
        
        if match_count == total_required and total_required > 0:
            return f"Exact category match: {', '.join(sorted(matching_categories)[:2])}"
        elif match_count >= 2:
            return f"Operates in {match_count} relevant categories"
        else:
            cat_name = list(matching_categories)[0]
            return f"Specializes in {cat_name}"

    def _get_industry_match_reason_semantic(self, tender_data: Dict, vendor_data: Dict) -> Optional[str]:
        """OPTIMIZED: Industry matching with batch embeddings"""
        tender_industry = (tender_data.get("industry") or "").strip()
        vendor_industries_raw = vendor_data.get("industries", []) or []
        vendor_industries = [vi.strip() for vi in vendor_industries_raw if vi]
        
        if not vendor_industries or not tender_industry:
            return None
        
        tender_words = tender_industry.lower().split()
        generic_terms = {'manufacturing', 'processing', 'services', 'products', 'industries'}
        
        if len(tender_words) == 1 and tender_words[0] in generic_terms:
            if len(vendor_industries) >= 5:
                return f"Multi-industry supplier serving {len(vendor_industries)} sectors"
            return None
        
        try:
            tender_embedding = self.embedding_service.get_text_embedding(tender_industry)
            
            # BATCH EMBED: All vendor industries
            vendor_embeddings = self.embedding_service.get_text_embeddings_batch(vendor_industries)
            
            best_match = None
            best_score = 0.70
            
            for vendor_industry, vendor_emb in zip(vendor_industries, vendor_embeddings):
                if tender_industry.lower() == vendor_industry.lower():
                    return f"Experienced in {vendor_industry} industry"
                
                similarity = self._cosine_similarity(tender_embedding, vendor_emb)
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = vendor_industry
            
            if best_match:
                return f"Experienced in {best_match} industry"
            
            if len(vendor_industries) >= 5:
                return f"Multi-industry supplier serving {len(vendor_industries)} sectors"
            
        except Exception as e:
            logger.warning(f"Semantic industry matching failed: {e}")
            return self._get_industry_match_reason_fallback(tender_data, vendor_data)
        
        return None

    def _get_industry_match_reason_fallback(self, tender_data: Dict, vendor_data: Dict) -> Optional[str]:
        """Fallback industry matching"""
        tender_industry = (tender_data.get("industry") or "").lower().strip()
        vendor_industries = vendor_data.get("industries", []) or []
        
        if not tender_industry or not vendor_industries:
            return None
        
        tender_keywords = self._extract_industry_keywords(tender_industry)
        
        if not tender_keywords:
            if len(vendor_industries) >= 5:
                return f"Multi-industry supplier serving {len(vendor_industries)} sectors"
            return None
        
        for vendor_industry in vendor_industries:
            if not vendor_industry:
                continue
            
            vendor_keywords = self._extract_industry_keywords(vendor_industry.lower())
            overlap = tender_keywords & vendor_keywords
            
            if len(overlap) >= 2:
                return f"Experienced in {vendor_industry} industry"
        
        if len(vendor_industries) >= 5:
            return f"Multi-industry supplier serving {len(vendor_industries)} sectors"
        
        return None

    def _extract_industry_keywords(self, industry: str) -> Set[str]:
        """Extract meaningful keywords from industry names"""
        generic_terms = {
            'manufacturing', 'equipment', 'processing', 'products', 
            'materials', 'services', 'solutions', 'industries', 'devices',
            'systems', 'tools', 'supplies'
        }
        
        words = industry.lower().split()
        keywords = set()
        
        for word in words:
            word = word.strip('&,.-()[]{}')
            if len(word) > 3 and word not in generic_terms:
                keywords.add(word)
        
        return keywords

    def _get_geographic_match_reason(self, tender_data: Dict, vendor_data: Dict) -> Optional[str]:
        """Generate geographic capability reason"""
        state_pref = tender_data.get("state_preference", "pan_india")
        
        if state_pref == "pan_india":
            return "Available for Pan India supply"
        
        tender_states = set(tender_data.get("states", []) or [])
        vendor_states = set(vendor_data.get("states", []) or [])
        
        if not vendor_states:
            if tender_states:
                return "Can supply to all required locations"
            return "Pan India operations"
        
        matching_states = tender_states & vendor_states
        
        if not matching_states:
            return None
        
        match_count = len(matching_states)
        total_required = len(tender_states)
        
        if match_count == total_required:
            if match_count == 1:
                return f"Work in {list(matching_states)[0]}"
            else:
                return f"Operates in all {match_count} required states"
        else:
            states_list = sorted(matching_states)[:2]
            remaining = match_count - 2
            suffix = f" + {remaining} more" if remaining > 0 else ""
            return f"Presence in {', '.join(states_list)}{suffix}"

    def _get_capacity_match_reasons(self, tender_data: Dict, vendor_data: Dict) -> List[str]:
        """Generate business capacity reasons"""
        reasons = []
        
        business_type = vendor_data.get("business_type") or ""
        if business_type:
            type_lower = business_type.lower()
            if "manufacturer" in type_lower or "producer" in type_lower:
                reasons.append("Direct manufacturer (no intermediaries)")
            elif "supplier" in type_lower or "distributor" in type_lower:
                reasons.append(f"Established {business_type}")
        
        vendor_turnover = vendor_data.get("annual_turnover") or ""
        required_turnover = tender_data.get("required_annual_turnover") or ""
        
        if vendor_turnover and required_turnover:
            if self._meets_turnover_requirement(required_turnover, vendor_turnover):
                try:
                    req_idx = self.turnover_hierarchy.index(required_turnover)
                    vendor_idx = self.turnover_hierarchy.index(vendor_turnover)
                    
                    if vendor_idx > req_idx + 1:
                        reasons.append(f"Strong financial capacity ({vendor_turnover})")
                    elif vendor_idx == req_idx:
                        reasons.append(f"Meets turnover requirement ({vendor_turnover})")
                except (ValueError, IndexError):
                    pass
        elif vendor_turnover:
            reasons.append(f"Annual turnover: {vendor_turnover}")
        
        return reasons

    def _get_expertise_match_reason_semantic(self, tender_data: Dict, vendor_data: Dict) -> Optional[str]:
        """OPTIMIZED: Expertise matching (uses caching)"""
        vendor_desc = (vendor_data.get("description") or "").strip()
        
        if not vendor_desc or len(vendor_desc) < 50:
            return None
        
        tender_title = (tender_data.get("tender_title") or "").strip()
        tender_desc = (tender_data.get("brief_description") or "").strip()
        tender_text = f"{tender_title}. {tender_desc}"
        
        if not tender_text or len(tender_text) < 10:
            return None
        
        try:
            # Both embeddings will be cached
            tender_embedding = self.embedding_service.get_text_embedding(tender_text)
            vendor_embedding = self.embedding_service.get_text_embedding(vendor_desc[:500])
            
            similarity = self._cosine_similarity(tender_embedding, vendor_embedding)
            
            if similarity >= 0.75:
                return "Strong expertise alignment with tender requirements"
            elif similarity >= 0.65:
                return "Relevant experience for this requirement"
            
            vendor_desc_lower = vendor_desc.lower()
            if "leading" in vendor_desc_lower or "leader" in vendor_desc_lower:
                return "Industry leader with proven track record"
            elif "established" in vendor_desc_lower:
                import re
                years_match = re.search(r'(\d{4})|(\d+)\s*years', vendor_desc_lower)
                if years_match:
                    return "Established player with long-term experience"
        
        except Exception as e:
            logger.warning(f"Semantic expertise matching failed: {e}")
            return self._get_expertise_match_reason_fallback(tender_data, vendor_data)
        
        return None

    def _get_expertise_match_reason_fallback(self, tender_data: Dict, vendor_data: Dict) -> Optional[str]:
        """Fallback keyword-based expertise matching"""
        vendor_desc = (vendor_data.get("description") or "").lower()
        tender_title = (tender_data.get("tender_title") or "").lower()
        tender_desc = (tender_data.get("brief_description") or "").lower()
        
        if not vendor_desc:
            return None
        
        tender_keywords = self._extract_keywords(f"{tender_title} {tender_desc}")
        desc_keywords = self._extract_keywords(vendor_desc)
        overlap = tender_keywords & desc_keywords
        
        if len(overlap) >= 5:
            return "Strong expertise alignment with tender requirements"
        elif len(overlap) >= 3:
            return "Relevant experience for this requirement"
        
        if "leading" in vendor_desc or "leader" in vendor_desc:
            return "Industry leader with proven track record"
        elif "established" in vendor_desc:
            import re
            years_match = re.search(r'(\d{4})|(\d+)\s*years', vendor_desc)
            if years_match:
                return "Established player with long-term experience"
        
        return None

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text"""
        if not text:
            return set()
        
        stop_words = {
            'and', 'or', 'the', 'for', 'with', 'from', 'supply', 'procurement', 
            'various', 'including', 'such', 'requirement', 'requirements', 'etc',
            'across', 'multiple', 'quality', 'timely', 'delivery', 'services',
            'products', 'solutions', 'equipment', 'materials'
        }
        
        words = text.lower().split()
        keywords = set()
        
        for word in words:
            if not word:
                continue
            word = word.strip('.,;:()[]{}')
            if len(word) > 3 and word not in stop_words:
                keywords.add(word)
        
        return keywords

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Cosine similarity calculation failed: {e}")
            return 0.0

    def _calculate_match_score(
        self,
        tender_data: Dict,
        vendor_data: Dict,
        base_score: float
    ) -> float:
        """Enhanced match scoring with product multiplier"""
        
        score = base_score
        
        multipliers = [
            self._product_match_multiplier(tender_data, vendor_data),
            self._cert_multiplier(tender_data, vendor_data),
            self._category_multiplier(tender_data, vendor_data),
            self._geo_multiplier(tender_data, vendor_data),
            self._business_multiplier(vendor_data),
        ]
        
        for multiplier in multipliers:
            score *= multiplier
        
        return min(score, 1.0)

    def _cert_multiplier(self, tender_data: Dict, vendor_data: Dict) -> float:
        """Certification multiplier: 0.85 (penalty) to 1.25 (boost)"""
        required = set(tender_data.get("required_certifications", []) or [])
        if not required:
            return 1.0
        
        vendor = set(vendor_data.get("certifications", []) or [])
        overlap = required & vendor
        
        if not overlap:
            return 0.85
        
        match_ratio = len(overlap) / len(required)
        
        if match_ratio == 1.0:
            return 1.25
        else:
            return 1.0 + (0.20 * match_ratio)

    def _category_multiplier(self, tender_data: Dict, vendor_data: Dict) -> float:
        """Category multiplier: 1.0 (no match) to 1.15 (perfect match)"""
        tender_cats = set(tender_data.get("categories", []) or [])
        vendor_cats = set(vendor_data.get("categories", []) or [])
        
        if not tender_cats or not vendor_cats:
            return 1.0
        
        overlap = tender_cats & vendor_cats
        if not overlap:
            return 1.0
        
        match_ratio = len(overlap) / len(tender_cats)
        return 1.0 + (0.15 * match_ratio)

    def _geo_multiplier(self, tender_data: Dict, vendor_data: Dict) -> float:
        """Geographic multiplier: 0.80 (penalty) to 1.10 (boost)"""
        state_pref = tender_data.get("state_preference", "pan_india")
        
        if state_pref == "pan_india":
            return 1.05
        
        tender_states = set(tender_data.get("states", []) or [])
        vendor_states = set(vendor_data.get("states", []) or [])
        
        if not tender_states:
            return 1.0
        
        if not vendor_states:
            return 1.0
        
        overlap = tender_states & vendor_states
        
        if not overlap:
            return 0.80
        
        match_ratio = len(overlap) / len(tender_states)
        return 1.0 + (0.10 * match_ratio)

    def _business_multiplier(self, vendor_data: Dict) -> float:
        """Business type multiplier: 1.0 to 1.10"""
        business_type = (vendor_data.get("business_type") or "").lower()
        
        if "manufacturer" in business_type or "producer" in business_type:
            return 1.10
        elif "supplier" in business_type:
            return 1.05
        
        return 1.0
    
    def _meets_turnover_requirement(
        self, 
        required: Optional[str], 
        vendor_turnover: Optional[str]
    ) -> bool:
        if not required or not vendor_turnover:
            return True
        
        try:
            req_idx = self.turnover_hierarchy.index(required)
            vendor_idx = self.turnover_hierarchy.index(vendor_turnover)
            return vendor_idx >= req_idx
        except (ValueError, AttributeError):
            return True

    def update_vendor(self, vendor_id: str, update_data: Dict) -> Dict:
        """Update vendor information and regenerate embedding"""
        existing_vendor = self.db.get_vendor(vendor_id)
        
        if not existing_vendor:
            raise ValueError(f"Vendor {vendor_id} not found")
        
        updated_vendor = {**existing_vendor}
        
        for key, value in update_data.items():
            if value is not None:
                updated_vendor[key] = value
        
        new_embedding = self.embedding_service.generate_vendor_embedding(updated_vendor)
        
        self.db.add_vendor(vendor_id, new_embedding, updated_vendor)
        
        logger.info(f"Updated vendor: {vendor_id}")
        
        return {
            "status": "success",
            "vendor_id": vendor_id,
            "updated_fields": list(update_data.keys())
        }