# main.py - FastAPI application entry point
# Execução: uvicorn src.main:app --reload --port 8000
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from loguru import logger
import sys
import re

from src.config import settings
from src.infrastructure.database.connection import create_tables, engine
from src.infrastructure.rate_limiter import limiter, rate_limit_exceeded_handler
from src.interface.api.routers import operadoras, estatisticas
from src.interface.api.schemas import HealthCheckResponse, ErrorResponse
from slowapi.errors import RateLimitExceeded


# Configuração do Loguru (mais simples que logging padrão)
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
    colorize=True,
)

# Log para arquivo (opcional, descomente se quiser)
# logger.add(
#     "logs/app_{time}.log",
#     rotation="500 MB",
#     retention="10 days",
#     level=settings.LOG_LEVEL,
# )


# =============================================================
# LIFECYCLE EVENTS (Startup e Shutdown)
# =============================================================
# DECISÃO: Usar asynccontextmanager (FastAPI moderno).
# JUSTIFICATIVA:
# - Substitui on_startup/on_shutdown deprecated.
# - Garantia de cleanup com try/finally.
# - Permite inicialização de recursos async.
# =============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia ciclo de vida da aplicação.
    
    STARTUP:
    - Valida configurações de segurança.
    - Cria tabelas do banco (se não existirem).
    - Loga início da aplicação.
    
    SHUTDOWN:
    - Fecha conexões do banco.
    - Loga encerramento.
    """
    # === STARTUP ===
    logger.info("🚀 Iniciando aplicação...")
    
    # Validação de segurança para produção
    settings.validate_production_settings()
    
    logger.info(f"📊 Modo debug: {settings.API_DEBUG}")
    logger.info(f"🌍 Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"💾 Banco de dados: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")
    logger.info(f"🔒 CORS Origins: {settings.cors_origins_list}")
    
    # Cria tabelas (em dev; produção usaria migrations)
    try:
        create_tables()
        logger.info("✅ Tabelas do banco criadas/verificadas")
    except Exception as e:
        logger.warning(f"⚠️ Não foi possível criar tabelas: {e}")
        logger.warning("   Verifique se o MySQL está rodando e o banco existe")
    
    yield  # Aplicação roda aqui
    
    # === SHUTDOWN ===
    logger.info("🔌 Encerrando aplicação...")
    engine.dispose()  # Fecha pool de conexões
    logger.info("👋 Aplicação encerrada com sucesso")


# =============================================================
# CRIAÇÃO DA APLICAÇÃO FASTAPI
# =============================================================
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="""
    ## API de Análise de Despesas de Operadoras de Planos de Saúde
    
    Esta API fornece acesso aos dados de despesas das operadoras
    de planos de saúde registradas na ANS (Agência Nacional de Saúde Suplementar).
    
    ### Funcionalidades:
    
    * **Operadoras**: Listagem, busca e detalhes de operadoras
    * **Despesas**: Histórico de despesas por operadora
    * **Estatísticas**: Agregações e rankings
    
    ### Trade-offs Técnicos:
    
    * **Paginação**: Offset-based (simples, adequado para ~5000 operadoras)
    * **Cache**: In-memory para estatísticas (TTL 15 min)
    * **Banco**: MySQL 8.0 com SQLAlchemy ORM
    """,
    lifespan=lifespan,
    docs_url=None,  # Desabilitado - usando /docs customizado
    redoc_url=None,  # Desabilitado
    openapi_url=None,  # Desabilitado
)


# =============================================================
# SETUP RATE LIMITER
# =============================================================
# Configurado ANTES dos middlewares para capturar exceções corretamente
# =============================================================
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# =============================================================
# MIDDLEWARE: Security Headers
# =============================================================
# DECISÃO: Adicionar headers de segurança em todas as respostas.
# JUSTIFICATIVA:
# - Proteção contra clickjacking (X-Frame-Options)
# - Proteção contra XSS (X-Content-Type-Options)
# - Política de referrer para privacidade
# =============================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona headers de segurança em todas as respostas."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Proteção contra clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Previne MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Política de referrer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Proteção XSS (browsers modernos)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy básica
        if settings.ENVIRONMENT == "production":
            response.headers["Content-Security-Policy"] = "default-src 'self'"
            # HSTS para HTTPS (apenas em produção)
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

app.add_middleware(SecurityHeadersMiddleware)


# =============================================================
# MIDDLEWARE: CORS
# =============================================================
# DECISÃO: CORS configurável via variável de ambiente.
# JUSTIFICATIVA:
# - Segurança: Não usar wildcard (*) em produção.
# - Flexibilidade: Diferentes origens para dev/staging/prod.
# =============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Métodos específicos
    allow_headers=["*"],
)


# =============================================================
# Função para sanitizar URLs nos logs
# =============================================================
def sanitize_url_for_logging(url: str) -> str:
    """
    Remove informações sensíveis da URL antes de logar.
    
    SANITIZA:
    - Query strings com tokens/passwords
    - Parâmetros de API keys
    - Credenciais em URLs
    """
    # Remove query string completa (pode conter dados sensíveis)
    sanitized = re.sub(r'\?.*$', '?[REDACTED]', url) if '?' in url else url
    
    # Alternativa: remover apenas parâmetros específicos
    # sanitized = re.sub(r'(password|token|key|secret|api_key)=[^&]*', r'\1=[REDACTED]', url)
    
    return sanitized


# =============================================================
# MIDDLEWARE: Logging de Requests (Sanitizado)
# =============================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Loga todas as requisições HTTP de forma segura.
    
    SEGURANÇA:
    - Não loga query strings (podem conter tokens).
    - Não loga headers de autorização.
    - Não loga body de requests.
    """
    start_time = datetime.now()
    
    # Processa requisição
    response = await call_next(request)
    
    # Calcula tempo de resposta
    process_time = (datetime.now() - start_time).total_seconds() * 1000
    
    # Sanitiza URL antes de logar
    safe_path = sanitize_url_for_logging(str(request.url))
    
    # Loga requisição (sem dados sensíveis)
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Tempo: {process_time:.2f}ms"
    )
    
    return response


# =============================================================
# HANDLER DE EXCEÇÕES GLOBAIS
# =============================================================
# DECISÃO: Capturar exceções não tratadas e retornar JSON padronizado.
# JUSTIFICATIVA:
# - Evita expor stack traces em produção.
# - Resposta consistente para o frontend.
# - Loga erro completo para debugging.
# =============================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handler global para exceções não tratadas.
    
    COMPORTAMENTO:
    - Em DEBUG: Mostra mensagem e tipo da exceção.
    - Em PRODUÇÃO: Mostra mensagem genérica.
    - Sempre loga o erro completo.
    """
    logger.exception(f"Erro não tratado: {exc}")
    
    if settings.API_DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Erro interno do servidor",
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Erro interno do servidor",
                "detail": "Ocorreu um erro inesperado. Tente novamente mais tarde.",
            },
        )


# =============================================================
# REGISTRO DOS ROUTERS
# =============================================================
# Cada router agrupa endpoints relacionados.
# Prefixos são definidos nos próprios routers.
# =============================================================
app.include_router(operadoras.router)
app.include_router(estatisticas.router)


# =============================================================
# DOCUMENTAÇÃO CUSTOMIZADA (Template Externo)
# =============================================================
# Refatorado: HTML extraído para arquivo de template.
# Benefícios:
# - Código Python mais limpo (~100 linhas removidas)
# - Template editável por designers
# - Facilita customização do estilo
# =============================================================
from fastapi.responses import HTMLResponse
from pathlib import Path

DOCS_TEMPLATE_PATH = Path(__file__).parent / "interface" / "api" / "templates" / "docs.html"

@app.get("/docs", include_in_schema=False)
async def api_docs():
    """Swagger UI customizado - carrega template HTML externo."""
    try:
        html_content = DOCS_TEMPLATE_PATH.read_text(encoding="utf-8")
        # Substitui placeholders
        html_content = html_content.replace("{{version}}", settings.API_VERSION)
        return HTMLResponse(html_content)
    except FileNotFoundError:
        # Fallback minimalista se template não existir
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>API Docs</title></head>
        <body style="font-family: sans-serif; padding: 40px;">
            <h1>API de Análise de Despesas v{settings.API_VERSION}</h1>
            <p>Template de documentação não encontrado.</p>
            <p><a href="/openapi.json">OpenAPI JSON</a></p>
        </body>
        </html>
        """)


# =============================================================
# ENDPOINTS UTILITÁRIOS (fora dos routers)
# =============================================================
@app.get(
    "/",
    summary="Raiz da API",
    description="Retorna informações básicas da API.",
    tags=["Utilitários"],
)
async def root():
    """
    Endpoint raiz - informações da API.
    
    Útil para verificar se a API está no ar.
    """
    return {
        "message": "API de Análise de Despesas - Intuitive Care",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Verifica se a API está saudável.",
    tags=["Utilitários"],
)
async def health_check():
    """
    Health check para monitoramento.
    
    usado por:
    - Load balancers (verificar se instância está saudável).
    - Kubernetes (liveness/readiness probes).
    - Sistemas de monitoramento.
    """
    return HealthCheckResponse(
        status="healthy",
        version=settings.API_VERSION,
        timestamp=datetime.now(),
    )


@app.get(
    "/metrics",
    summary="Métricas da API",
    description="Retorna métricas de performance e uso da API.",
    tags=["Utilitários"],
)
async def metrics_endpoint():
    """
    Endpoint de métricas para observabilidade.
    
    Retorna:
    - Total de requisições
    - Taxa de erros
    - Tempo médio de resposta
    - Distribuição por status code
    - Top endpoints
    """
    try:
        from src.infrastructure.observability import metrics
        return metrics.get_metrics()
    except ImportError:
        return {
            "error": "Módulo de observabilidade não disponível",
            "message": "Use o módulo completo para métricas avançadas"
        }


@app.get(
    "/cache/stats",
    summary="Estatísticas de Cache",
    description="Retorna estatísticas dos caches da aplicação.",
    tags=["Utilitários"],
)
async def cache_stats():
    """
    Endpoint para monitorar performance dos caches.
    
    Retorna:
    - Hit rate de cada cache
    - Total de requisições
    - Status atual (válido/expirado)
    """
    from src.infrastructure.cache import CacheRegistry
    return {
        "caches": CacheRegistry.get_all_stats(),
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================
# EXECUÇÃO DIRETA (para desenvolvimento)
# =============================================================
# Permite rodar: python -m src.main
# Em produção, use: uvicorn src.main:app
# =============================================================
if __name__ == "__main__":
    import uvicorn
    
    logger.info("Iniciando servidor em modo desenvolvimento...")
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Hot reload em desenvolvimento
        log_level="info",
    )
