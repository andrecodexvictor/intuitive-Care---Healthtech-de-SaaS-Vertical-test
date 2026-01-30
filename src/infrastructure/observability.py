# =============================================================
# observability.py - Módulo de Observabilidade
# =============================================================
# IMPLEMENTA:
# - Logging estruturado com Loguru
# - Request tracing middleware
# - Métricas de performance
# - Health check
# =============================================================
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response
from loguru import logger
import sys

# =============================================================
# Configuração do Loguru
# =============================================================
# Remove handler padrão e configura formato estruturado
logger.remove()

# Console handler com formato legível para desenvolvimento
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{extra[request_id]}</cyan> | "
           "<level>{message}</level>",
    level="INFO",
    colorize=True,
    filter=lambda record: "request_id" in record["extra"]
)

# Fallback para logs sem request_id
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<level>{message}</level>",
    level="INFO",
    colorize=True,
    filter=lambda record: "request_id" not in record["extra"]
)

# File handler para persistência (logs rotativos)
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # Rotação diária à meia-noite
    retention="7 days",  # Manter 7 dias
    compression="zip",  # Comprimir logs antigos
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
           "{extra[request_id]} | {name}:{function}:{line} | {message}",
    filter=lambda record: "request_id" in record["extra"]
)


# =============================================================
# Métricas em Memória (Simples, sem Prometheus)
# =============================================================
class MetricsCollector:
    """
    Coletor de métricas simples em memória.
    
    Para produção real, substituir por Prometheus ou DataDog.
    """
    
    def __init__(self):
        self.request_count = 0
        self.request_duration_sum = 0.0
        self.request_errors = 0
        self.status_codes = {}
        self.endpoint_hits = {}
    
    def record_request(
        self, 
        endpoint: str, 
        status_code: int, 
        duration_ms: float
    ):
        """Registra métricas de uma requisição."""
        self.request_count += 1
        self.request_duration_sum += duration_ms
        
        if status_code >= 400:
            self.request_errors += 1
        
        # Contagem por status code
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        
        # Contagem por endpoint
        self.endpoint_hits[endpoint] = self.endpoint_hits.get(endpoint, 0) + 1
    
    def get_metrics(self) -> dict:
        """Retorna snapshot das métricas."""
        avg_duration = (
            self.request_duration_sum / self.request_count 
            if self.request_count > 0 else 0
        )
        error_rate = (
            self.request_errors / self.request_count * 100 
            if self.request_count > 0 else 0
        )
        
        return {
            "total_requests": self.request_count,
            "total_errors": self.request_errors,
            "error_rate_percent": round(error_rate, 2),
            "avg_response_time_ms": round(avg_duration, 2),
            "status_code_distribution": self.status_codes,
            "top_endpoints": dict(
                sorted(
                    self.endpoint_hits.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]
            )
        }
    
    def reset(self):
        """Reset das métricas (útil para testes)."""
        self.__init__()


# Instância global do coletor
metrics = MetricsCollector()


# =============================================================
# Request Tracing Middleware
# =============================================================
async def request_tracing_middleware(request: Request, call_next: Callable):
    """
    Middleware que adiciona:
    - Request ID único para rastreamento
    - Logging de entrada/saída
    - Medição de tempo de resposta
    - Coleta de métricas
    """
    # Gerar ID único para a requisição
    request_id = str(uuid.uuid4())[:8]
    
    # Adicionar ao contexto do request
    request.state.request_id = request_id
    
    # Log de entrada
    start_time = time.perf_counter()
    with logger.contextualize(request_id=request_id):
        logger.info(
            f"→ {request.method} {request.url.path} "
            f"| Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Processar requisição
        try:
            response: Response = await call_next(request)
            
            # Calcular duração
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Registrar métricas
            metrics.record_request(
                endpoint=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms
            )
            
            # Log de saída
            log_level = "INFO" if response.status_code < 400 else "WARNING"
            logger.log(
                log_level,
                f"← {response.status_code} | {duration_ms:.2f}ms"
            )
            
            # Adicionar headers de observabilidade
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
            
            return response
            
        except Exception as e:
            # Log de erro
            duration_ms = (time.perf_counter() - start_time) * 1000
            metrics.record_request(
                endpoint=request.url.path,
                status_code=500,
                duration_ms=duration_ms
            )
            logger.exception(f"✗ EXCEPTION | {duration_ms:.2f}ms | {str(e)}")
            raise


# =============================================================
# Health Check
# =============================================================
async def health_check() -> dict:
    """
    Endpoint de health check básico.
    
    Em produção, adicionar:
    - Verificação de conexão com banco
    - Verificação de serviços externos
    - Verificação de espaço em disco
    """
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": "1.0.0",
        "service": "intuitive-care-api"
    }


# =============================================================
# Métricas Endpoint
# =============================================================
async def get_metrics() -> dict:
    """Retorna métricas coletadas."""
    return metrics.get_metrics()


# =============================================================
# Logger Helpers
# =============================================================
def log_business_event(event_name: str, **kwargs):
    """
    Log de eventos de negócio (auditoria).
    
    Exemplo:
        log_business_event("operadora_viewed", cnpj="12345678000190")
    """
    logger.bind(**kwargs).info(f"[BUSINESS] {event_name}")


def log_performance_warning(operation: str, duration_ms: float, threshold_ms: float):
    """
    Log de alerta de performance.
    
    Exemplo:
        log_performance_warning("db_query", 1500, 1000)
    """
    if duration_ms > threshold_ms:
        logger.warning(
            f"[PERF] {operation} took {duration_ms:.2f}ms "
            f"(threshold: {threshold_ms}ms)"
        )
