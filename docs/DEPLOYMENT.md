# AI Perp DEX - Deployment Guide

## Table of Contents
- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Fly.io Deployment](#flyio-deployment)
- [Railway Deployment](#railway-deployment)
- [Environment Configuration](#environment-configuration)
- [Scaling](#scaling)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/your-org/ai-perp-dex.git
cd ai-perp-dex

# Copy environment config
cp deploy/.env.example .env
# Edit .env with your settings

# Start with Docker Compose
docker-compose up -d
```

Access:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8082
- **API Docs**: http://localhost:8082/docs (FastAPI auto-docs)

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- Redis 7+

### API Server

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
cd trading-hub
pip install -r requirements.txt

# Set environment variables
export REDIS_URL=redis://localhost:6379
export JWT_SECRET=dev-secret-key

# Run the server
uvicorn api.server:app --reload --port 8082
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Redis

```bash
# macOS
brew install redis
redis-server

# Docker
docker run -d -p 6379:6379 redis:7-alpine
```

---

## Docker Deployment

### Build Images

```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build api
```

### Run Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Production Mode

```bash
# Use production profile (includes nginx)
docker-compose --profile production up -d
```

### Individual Containers

```bash
# API only
docker build --target api -t ai-perp-dex-api .
docker run -d -p 8082:8082 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e JWT_SECRET=your-secret \
  ai-perp-dex-api

# Frontend only
docker build --target frontend -t ai-perp-dex-frontend .
docker run -d -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://api:8082 \
  ai-perp-dex-frontend
```

---

## Fly.io Deployment

### Initial Setup

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Create app
fly launch --name ai-perp-dex --region sjc
```

### Configure Secrets

```bash
# Required secrets
fly secrets set JWT_SECRET="your-production-jwt-secret-min-32-chars"
fly secrets set HYPERLIQUID_API_KEY="your-hl-key"  # if using external routing
```

### Deploy

```bash
# Deploy API
fly deploy

# Scale
fly scale count 2 --region sjc,lax

# Check status
fly status
fly logs
```

### Redis on Fly.io

Option 1: Fly Redis (managed)
```bash
fly redis create
# Note the connection URL
fly secrets set REDIS_URL="redis://..."
```

Option 2: Upstash Redis (serverless)
```bash
# Create at upstash.com
fly secrets set REDIS_URL="rediss://your-upstash-url"
```

### Custom Domains

```bash
fly certs add your-domain.com
# Update DNS with the provided IP
```

---

## Railway Deployment

### Via Dashboard

1. Go to [railway.app](https://railway.app)
2. Create New Project
3. Deploy from GitHub repo
4. Railway auto-detects `railway.json`

### Via CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### Configure Variables

In Railway Dashboard:
1. Go to Variables tab
2. Add required secrets:
   - `JWT_SECRET`
   - `HYPERLIQUID_API_KEY`

### Add Redis

```bash
# Add Redis plugin
railway add redis

# The REDIS_URL will be auto-injected
```

---

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `JWT_SECRET` | JWT signing key (32+ chars) | `your-super-secret-key` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `API_ENV` | Environment mode | `production` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `MAX_CONCURRENT_REQUESTS` | `100` | Max concurrent connections |
| `RATE_LIMIT_PER_AGENT` | `10` | Per-agent rate limit |
| `GLOBAL_RATE_LIMIT` | `500` | Global rate limit |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins |

See `deploy/.env.example` for full list.

---

## Scaling

### Horizontal Scaling

```bash
# Fly.io
fly scale count 3

# Railway
# Use dashboard to adjust replica count

# Docker Compose
docker-compose up -d --scale api=3
```

### Vertical Scaling

```bash
# Fly.io
fly scale vm shared-cpu-2x
fly scale memory 1024

# Docker Compose - edit docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### Load Balancing

For Docker deployments, add nginx:

```nginx
upstream api {
    least_conn;
    server api1:8082;
    server api2:8082;
    server api3:8082;
}

server {
    listen 80;
    location /api {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8082/health

# Full stats
curl http://localhost:8082/stats
```

### Logging

```bash
# Docker logs
docker-compose logs -f --tail=100

# Fly.io logs
fly logs -a ai-perp-dex

# Railway logs
railway logs
```

### Metrics (Optional)

Enable Prometheus metrics:

```bash
# Set environment variable
METRICS_ENABLED=true
METRICS_PORT=9091

# Scrape endpoint
curl http://localhost:9091/metrics
```

### Alerts

Monitor these key metrics:
- Response time > 500ms
- Error rate > 1%
- Memory usage > 80%
- Active connections > 80

---

## Troubleshooting

### Common Issues

**1. Redis Connection Failed**
```bash
# Check Redis is running
redis-cli ping

# Check connection URL
echo $REDIS_URL
```

**2. CORS Errors**
```bash
# Update ALLOWED_ORIGINS
ALLOWED_ORIGINS=https://your-frontend.com,https://api.your-domain.com
```

**3. WebSocket Connection Issues**
```bash
# Ensure WS URL uses correct protocol
NEXT_PUBLIC_WS_URL=wss://api.your-domain.com/ws  # https = wss
```

**4. Out of Memory**
```bash
# Increase memory limit
fly scale memory 1024  # Fly.io

# Or in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G
```

**5. Slow Price Updates**
```bash
# Check price feed
curl http://localhost:8082/prices

# Restart price feed
docker-compose restart api
```

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=DEBUG docker-compose up

# API debug endpoint
curl http://localhost:8082/stats
```

### Support

- GitHub Issues: https://github.com/your-org/ai-perp-dex/issues
- Discord: https://discord.gg/your-server

---

## Security Checklist

Before going to production:

- [ ] Change `JWT_SECRET` (min 32 random characters)
- [ ] Set `API_ENV=production`
- [ ] Configure `ALLOWED_ORIGINS` (no wildcards)
- [ ] Enable HTTPS
- [ ] Set up rate limiting
- [ ] Configure firewall rules
- [ ] Set up monitoring & alerts
- [ ] Backup Redis data
- [ ] Review API key permissions
