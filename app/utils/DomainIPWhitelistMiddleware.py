from fastapi import Request
from urllib.parse import urlparse
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DomainIPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware to restrict access by IP address and/or domain"""
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove port if present for matching
            domain_without_port = domain.split(':')[0] if ':' in domain else domain
            return domain
        except Exception:
            return "";
    
    def _check_domain_match(self, domain: str, allowed_domains: set) -> bool:
        """Check if domain matches any allowed domain"""
        if not domain:
            return False
        
        # Direct match
        if domain in allowed_domains:
            return True
        
        # Match without port
        domain_without_port = domain.split(':')[0] if ':' in domain else domain
        for allowed in allowed_domains:
            allowed_without_port = allowed.split(':')[0] if ':' in allowed else allowed
            if domain_without_port == allowed_without_port:
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        # Public endpoints - always accessible
        public_paths = ["/", "/health", "/docs", "/redoc", "/openapi.json"]
        if request.url.path in public_paths:
            return await call_next(request)
        
        client_ip = request.client.host
        
        # Get allowed IPs and domains from settings
        allowed_ips = set(getattr(settings, 'ALLOWED_IPS', []))
        allowed_domains = set(getattr(settings, 'ALLOWED_DOMAINS', []))
        
        # If no restrictions configured, allow all
        if not allowed_ips and not allowed_domains:
            logger.debug(f"No restrictions configured, allowing access from {client_ip}")
            return await call_next(request)
        
        # Check IP whitelist
        if allowed_ips and client_ip in allowed_ips:
            logger.info(f"✓ Access granted via IP: {client_ip} on {request.url.path}")
            return await call_next(request)
        
        # Check domain whitelist via Origin or Referer header
        if allowed_domains:
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")
            host = request.headers.get("host", "")
            
            origin_domain = self._extract_domain(origin)
            referer_domain = self._extract_domain(referer)
            
            if self._check_domain_match(origin_domain, allowed_domains):
                logger.info(f"✓ Access granted via Origin: {origin_domain} (IP: {client_ip}) on {request.url.path}")
                return await call_next(request)
            
            if self._check_domain_match(referer_domain, allowed_domains):
                logger.info(f"✓ Access granted via Referer: {referer_domain} (IP: {client_ip}) on {request.url.path}")
                return await call_next(request)
            
            if self._check_domain_match(host, allowed_domains):
                logger.info(f"✓ Access granted via Host: {host} (IP: {client_ip}) on {request.url.path}")
                return await call_next(request)
        
        # Access denied - return JSON response instead of raising exception
        logger.warning(
            f"✗ Access DENIED - IP: {client_ip}, "
            f"Origin: {request.headers.get('origin', 'none')}, "
            f"Referer: {request.headers.get('referer', 'none')}, "
            f"Host: {request.headers.get('host', 'none')}, "
            f"Path: {request.url.path}"
        )
        
        return JSONResponse(
            status_code=403,
            content={
                "error": "Access Forbidden",
                "message": f"Your IP ({client_ip}) or domain is not authorized to access this resource.",
                "ip": client_ip,
                "path": request.url.path
            }
        )