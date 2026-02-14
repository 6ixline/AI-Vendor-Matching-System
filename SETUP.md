# Setup & Deployment Guide

Complete guide to setting up and deploying the AI Vendor Matching Engine.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment](#production-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Configuration Guide](#configuration-guide)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python 3.9+** (3.10 or 3.11 recommended)
- **pip** (latest version)
- **Docker & Docker Compose** (for Qdrant)
- **Git**
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))

### Recommended Tools

- **Postman** or **Insomnia** (API testing)
- **VS Code** with Python extension
- **curl** or **httpie** (CLI testing)

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Disk | 10 GB | 20+ GB (for logs & cache) |
| OS | Linux/macOS/Windows | Linux (Ubuntu 22.04) |

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/6ixline/AI-Vendor-Matching-System.git
cd ai-vendor-matching-engine
```

### Step 2: Create Virtual Environment

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt
```

**requirements.txt:**
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
qdrant-client==1.7.0
openai==1.10.0
numpy==1.26.3
python-multipart==0.0.6
```

### Step 4: Start Qdrant Vector Database

**Using Docker:**
```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant
```

**Verify Qdrant is running:**
```bash
curl http://localhost:6333/
# Should return: {"title":"qdrant - vector search engine","version":"1.7.4"}
```

**Qdrant Dashboard:**
Visit http://localhost:6333/dashboard to access the web UI.

### Step 5: Configure Environment

Create `.env` file in project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```properties
# Application Settings
APP_NAME=AI-Matching-Engine
APP_VERSION=1.0.0
DEBUG=True
ENV=development

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_VENDORS=vendors
QDRANT_COLLECTION_TENDERS=tenders
QDRANT_COLLECTION_FEEDBACK=feedback

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_DIMENSION=1536

# OpenAI API
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx  # ← Add your key here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# CORS (for web frontends)
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8000","*"]

# Matching Algorithm Parameters
DEFAULT_TOP_K=5
SIMILARITY_THRESHOLD=0.5
FEEDBACK_ADJUSTMENT_WEIGHT=0.1

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### Step 6: Initialize Database Collections

Run the initialization script:

```bash
python scripts/init_db.py
```

This creates the necessary Qdrant collections with proper schema.

### Step 7: Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Output should show:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 8: Verify Installation

**1. Check API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**2. Health Check:**
```bash
curl http://localhost:8000/api/v1/system/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "stats": {
    "vendors_count": 0,
    "tenders_count": 0
  }
}
```

**3. Test Vendor Creation:**
```bash
curl -X POST http://localhost:8000/api/v1/vendors/ \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_id": "V001",
    "company_name": "Test Corp",
    "description": "Test company",
    "industries": ["IT"],
    "categories": ["Software"],
    "products": ["SaaS"],
    "business_type": "Private Limited",
    "states": ["Maharashtra"],
    "certifications": ["ISO 9001"]
  }'
```

## Production Deployment

### Architecture Overview

```
Internet
   │
   ▼
[Nginx/Traefik]  ← Reverse Proxy + SSL
   │
   ▼
[Uvicorn Workers] ← FastAPI (4-8 workers)
   │
   ├─► [Qdrant Cluster] ← Vector Database
   │
   └─► [Redis] ← Distributed Cache (optional)
```

### Step 1: Production Dependencies

Install additional production packages:

```bash
pip install gunicorn python-json-logger sentry-sdk
```

### Step 2: Gunicorn Configuration

Create `gunicorn_config.py`:

```python
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "/var/log/matching-engine/access.log"
errorlog = "/var/log/matching-engine/error.log"
loglevel = "info"

# Process naming
proc_name = "ai-matching-engine"

# Server mechanics
daemon = False
pidfile = "/var/run/matching-engine.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if not using reverse proxy)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
```

### Step 3: Systemd Service

Create `/etc/systemd/system/matching-engine.service`:

```ini
[Unit]
Description=AI Vendor Matching Engine
After=network.target

[Service]
Type=notify
User=appuser
Group=appuser
WorkingDirectory=/opt/ai-vendor-matching-engine
Environment="PATH=/opt/ai-vendor-matching-engine/venv/bin"
ExecStart=/opt/ai-vendor-matching-engine/venv/bin/gunicorn \
    -c gunicorn_config.py \
    app.main:app

# Restart policy
Restart=on-failure
RestartSec=5s

# Logging
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable matching-engine
sudo systemctl start matching-engine
sudo systemctl status matching-engine
```

### Step 4: Nginx Configuration

Create `/etc/nginx/sites-available/matching-engine`:

```nginx
upstream matching_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/matching_engine_access.log;
    error_log /var/log/nginx/matching_engine_error.log;

    # Max upload size
    client_max_body_size 10M;

    # Proxy settings
    location / {
        proxy_pass http://matching_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://matching_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/matching-engine /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 5: SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

## Docker Deployment

### Full Stack with Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: matching-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    restart: unless-stopped
    networks:
      - matching-network

  api:
    build: .
    container_name: matching-api
    ports:
      - "8000:8000"
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    env_file:
      - .env
    depends_on:
      - qdrant
    restart: unless-stopped
    networks:
      - matching-network
    volumes:
      - ./logs:/app/logs

  redis:
    image: redis:7-alpine
    container_name: matching-redis
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - matching-network
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  qdrant_storage:
  redis_data:

networks:
  matching-network:
    driver: bridge
```

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Deploy:**
```bash
docker-compose up -d
docker-compose logs -f api  # View logs
```

## Configuration Guide

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | ✅ Yes |
| `QDRANT_HOST` | Qdrant server host | localhost | No |
| `QDRANT_PORT` | Qdrant server port | 6333 | No |
| `EMBEDDING_MODEL` | OpenAI model name | text-embedding-3-small | No |
| `DEFAULT_TOP_K` | Default recommendations | 5 | No |
| `SIMILARITY_THRESHOLD` | Min match score | 0.5 | No |
| `FEEDBACK_ADJUSTMENT_WEIGHT` | Learning rate | 0.1 | No |
| `LOG_LEVEL` | Logging verbosity | INFO | No |

### Tuning Parameters

#### Similarity Threshold
```properties
# Lower = more permissive (more results)
# Higher = stricter (fewer, higher quality results)

SIMILARITY_THRESHOLD=0.3  # Exploratory phase
SIMILARITY_THRESHOLD=0.5  # Balanced (recommended)
SIMILARITY_THRESHOLD=0.7  # Precision-focused
```

#### Feedback Learning Rate
```properties
# Lower = slower learning (more stable)
# Higher = faster learning (more responsive)

FEEDBACK_ADJUSTMENT_WEIGHT=0.05  # Conservative
FEEDBACK_ADJUSTMENT_WEIGHT=0.1   # Recommended
FEEDBACK_ADJUSTMENT_WEIGHT=0.2   # Aggressive
```

## Testing

### Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_matching.py -v
```

### Integration Tests

Create `tests/integration/test_e2e.py`:

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_full_matching_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Add vendor
        vendor_response = await client.post("/api/v1/vendors/", json={
            "vendor_id": "TEST_V001",
            "company_name": "Test Corp",
            "industries": ["IT"],
            "categories": ["Software"],
            "products": ["SaaS"],
            "business_type": "Private Limited",
            "states": ["Maharashtra"],
            "certifications": []
        })
        assert vendor_response.status_code == 201

        # 2. Get recommendations
        tender_response = await client.post("/api/v1/matching/recommend", json={
            "tender_id": "TEST_T001",
            "tender_title": "Software Development",
            "brief_description": "Need SaaS development",
            "industry": "IT",
            "categories": ["Software"],
            "state_preference": "pan_india",
            "states": []
        })
        assert tender_response.status_code == 200
        data = tender_response.json()
        assert len(data["matches"]) > 0
        assert data["matches"][0]["vendor_id"] == "TEST_V001"

        # 3. Submit feedback
        feedback_response = await client.post("/api/v1/feedback/", json={
            "tender_id": "TEST_T001",
            "vendor_id": "TEST_V001",
            "match_success": True,
            "selected": True,
            "rating": 5
        })
        assert feedback_response.status_code == 200
```

### Load Testing

Using `locust`:

```python
# locustfile.py
from locust import HttpUser, task, between

class MatchingEngineUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def get_recommendations(self):
        self.client.post("/api/v1/matching/recommend", json={
            "tender_id": "LOAD_TEST",
            "tender_title": "Test Tender",
            "brief_description": "Load testing",
            "industry": "IT",
            "categories": ["Software"],
            "state_preference": "pan_india",
            "states": []
        })
    
    @task(1)
    def health_check(self):
        self.client.get("/api/v1/system/health")
```

**Run load test:**
```bash
locust -f locustfile.py --host=http://localhost:8000
```

## Troubleshooting

### Common Issues

#### 1. Qdrant Connection Failed

**Error:** `ConnectionError: Cannot connect to Qdrant`

**Solution:**
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check logs
docker logs qdrant

# Restart Qdrant
docker restart qdrant
```

#### 2. OpenAI API Rate Limit

**Error:** `RateLimitError: Rate limit exceeded`

**Solutions:**
- Increase cache TTL to reduce API calls
- Implement request queuing
- Upgrade OpenAI tier

```properties
# In .env - increase cache duration
CACHE_TTL=86400  # 24 hours → 48 hours
```

#### 3. Slow Query Performance

**Issue:** Searches taking >500ms

**Diagnosis:**
```bash
# Check Qdrant collection size
curl http://localhost:6333/collections/vendors

# Check index parameters
```

**Solutions:**
- Increase `ef` parameter in HNSW config
- Add more filtering at application level
- Consider result caching

#### 4. Memory Issues

**Error:** `MemoryError: Cannot allocate vector`

**Solution:**
```bash
# Check cache size
curl http://localhost:8000/api/v1/system/stats

# Clear cache
# POST http://localhost:8000/api/v1/system/clear-cache
```

### Debug Mode

Enable detailed logging:

```properties
# .env
DEBUG=True
LOG_LEVEL=DEBUG
```

View logs:
```bash
tail -f logs/app.log
```

### Health Monitoring

```bash
# System stats
curl http://localhost:8000/api/v1/system/stats

# Response:
{
  "vendors_count": 1523,
  "tenders_count": 342,
  "cache_size": 8456,
  "cache_hit_rate": 0.87
}
```

---

## Next Steps

1. ✅ Complete local setup
2. ✅ Run tests to verify
3. ✅ Load sample data
4. ✅ Test API endpoints
5. 🔜 Deploy to production
6. 🔜 Set up monitoring
7. 🔜 Configure backups

For additional help, see:
- [API Documentation](http://localhost:8000/docs)
- [Architecture Guide](ARCHITECTURE.md)
- [GitHub Issues](https://github.com/6ixline/AI-Vendor-Matching-System/issues)