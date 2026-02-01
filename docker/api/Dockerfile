# =============================================================
# Dockerfile.api - Backend FastAPI (Python)
# =============================================================
# MULTI-STAGE BUILD para imagem otimizada
# Imagem final ~200MB ao invés de ~1GB
# =============================================================

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Instala dependências de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements primeiro (cache de layers)
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copia dependências instaladas do builder
COPY --from=builder /root/.local /root/.local

# Adiciona binários ao PATH
ENV PATH=/root/.local/bin:$PATH

# Copia código da aplicação
COPY src/ ./src/
COPY run_etl.py .
COPY seed_database.py .
COPY sql/ ./sql/

# Cria diretório de dados
RUN mkdir -p /app/data /app/logs

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DATABASE_HOST=mysql
ENV DATABASE_PORT=3306
ENV DATABASE_USER=root
ENV DATABASE_PASSWORD=intuitive_care_2024
ENV DATABASE_NAME=intuitive_care_test
ENV API_DEBUG=false
ENV ENVIRONMENT=production

# Expõe porta da API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Comando padrão: inicia API
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
