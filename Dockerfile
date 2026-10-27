# Sentiq web version (FastAPI + React). The Streamlit version deploys separately on Streamlit Community Cloud.
# Build:  docker build -t sentiq .
# Run:    docker run -p 8000:8000 sentiq      then open http://localhost:8000

# ---- 1. build the web interface ----
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# ---- 2. Python runtime ----
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8000
WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY src/ src/
COPY api/ api/
COPY config/ config/
COPY data/ data/
COPY models/ models/
COPY --from=web /web/dist web/dist
# run as an unprivileged user
RUN useradd --create-home sentiq && chown -R sentiq /app
USER sentiq
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health')"
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
