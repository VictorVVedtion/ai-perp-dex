# AI Perp DEX - Trading Hub Dockerfile
# Multi-stage build for production

# ============================================
# Stage 1: Python API Server
# ============================================
FROM python:3.11-slim as api

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY trading-hub/requirements.txt .

# Create requirements.txt if not exists
RUN if [ ! -f requirements.txt ]; then \
    echo "fastapi==0.109.0\nuvicorn[standard]==0.27.0\npydantic==2.6.0\nwebsockets==12.0\nhttpx==0.26.0\naiohttp==3.9.1\nredis==5.0.1\npython-jose[cryptography]==3.3.0\npasslib[bcrypt]==1.7.4" > requirements.txt; \
    fi

RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY trading-hub/ ./trading-hub/
COPY middleware/ ./middleware/ 2>/dev/null || mkdir -p ./middleware

# Set Python path
ENV PYTHONPATH=/app/trading-hub

# Expose API port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8082/health')"

# Run the API server
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8082"]


# ============================================
# Stage 2: Frontend Build
# ============================================
FROM node:20-alpine as frontend-builder

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source
COPY frontend/ ./

# Build production bundle
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


# ============================================
# Stage 3: Frontend Production
# ============================================
FROM node:20-alpine as frontend

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy only necessary files
COPY --from=frontend-builder /app/public ./public
COPY --from=frontend-builder /app/.next/standalone ./
COPY --from=frontend-builder /app/.next/static ./.next/static

# Expose frontend port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["node", "server.js"]
