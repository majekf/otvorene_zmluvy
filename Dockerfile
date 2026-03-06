# ---- Backend Stage ----
FROM python:3.12-slim AS backend

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY src/ src/
COPY scripts/ scripts/
COPY data/ data/
COPY scrape_crz.py ./

# ---- Frontend Build Stage ----
FROM node:22-slim AS frontend-build

WORKDIR /app/frontend

# Install Node dependencies
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# ---- Final Stage ----
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY src/ src/
COPY scripts/ scripts/
COPY data/ data/
COPY scrape_crz.py ./

# Copy built frontend assets
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Environment defaults
ENV GOVLENS_HOST=0.0.0.0
ENV GOVLENS_PORT=8000
ENV GOVLENS_DATA_PATH=data/sample_contracts.json
ENV LLM_PROVIDER=mock

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/chat/status')" || exit 1

# Start the FastAPI server (serves API + static frontend)
CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
