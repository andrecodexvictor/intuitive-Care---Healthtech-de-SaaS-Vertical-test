# cache.py - Cache genérico com TTL
# Classe reutilizável para evitar variáveis globais duplicadas
from datetime import datetime, timedelta
from typing import TypeVar, Generic, Optional, Callable, Any
from functools import wraps
from threading import Lock
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TTLCache(Generic[T]):
    """
    Cache em memória com TTL configurável. Thread-safe.
    
    Exemplo:
        cache = TTLCache[dict](ttl_minutes=15)
        cache.set({"total": 1000})
        result = cache.get()  # None após 15 minutos
    """
    
    def __init__(self, ttl_minutes: int = 15, name: str = "default"):
        """Inicializa cache com TTL em minutos."""
        self._ttl = timedelta(minutes=ttl_minutes)
        self._data: Optional[T] = None
        self._timestamp: Optional[datetime] = None
        self._lock = Lock()
        self._name = name
        self._hits = 0
        self._misses = 0
    
    def get(self) -> Optional[T]:
        """Retorna dados se válidos, None se expirado."""
        with self._lock:
            if self._data is None:
                self._misses += 1
                return None
            
            if self._is_expired():
                logger.debug(f"Cache '{self._name}' expirado")
                self._data = None
                self._timestamp = None
                self._misses += 1
                return None
            
            self._hits += 1
            logger.debug(f"Cache '{self._name}' hit")
            return self._data
    
    def set(self, data: T) -> None:
        """Armazena dados no cache com timestamp atual."""
        with self._lock:
            self._data = data
            self._timestamp = datetime.now()
            logger.debug(f"Cache '{self._name}' atualizado")
    
    def invalidate(self) -> None:
        """
        Invalida o cache (remove dados e timestamp).
        
        Útil para forçar recálculo após atualização de dados.
        """
        with self._lock:
            self._data = None
            self._timestamp = None
            logger.debug(f"Cache '{self._name}' invalidado")
    
    def _is_expired(self) -> bool:
        """Verifica se o cache expirou baseado no TTL."""
        if self._timestamp is None:
            return True
        return datetime.now() - self._timestamp > self._ttl
    
    @property
    def stats(self) -> dict:
        """Retorna estatísticas do cache."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "name": self._name,
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "ttl_minutes": self._ttl.total_seconds() / 60,
            "is_valid": self._data is not None and not self._is_expired(),
        }
    
    def __repr__(self) -> str:
        status = "valid" if self._data and not self._is_expired() else "empty/expired"
        return f"TTLCache(name='{self._name}', status={status}, ttl={self._ttl})"


class CacheRegistry:
    """
    Registro centralizado de caches para observabilidade.
    
    Permite monitorar e gerenciar todos os caches da aplicação.
    """
    
    _caches: dict[str, TTLCache] = {}
    
    @classmethod
    def register(cls, cache: TTLCache) -> None:
        """Registra um cache no registry."""
        cls._caches[cache._name] = cache
    
    @classmethod
    def get_all_stats(cls) -> list[dict]:
        """Retorna estatísticas de todos os caches registrados."""
        return [cache.stats for cache in cls._caches.values()]
    
    @classmethod
    def invalidate_all(cls) -> None:
        """Invalida todos os caches registrados."""
        for cache in cls._caches.values():
            cache.invalidate()
        logger.info(f"Todos os {len(cls._caches)} caches invalidados")


def cached(cache: TTLCache[T]) -> Callable:
    """
    Decorator para cachear resultado de funções.
    
    EXEMPLO:
        >>> stats_cache = TTLCache[dict](ttl_minutes=15, name="stats")
        >>> 
        >>> @cached(stats_cache)
        >>> def get_statistics() -> dict:
        ...     # Cálculo custoso
        ...     return {"total": calcular_total()}
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Tenta cache primeiro
            result = cache.get()
            if result is not None:
                return result
            
            # Calcula e armazena
            result = func(*args, **kwargs)
            cache.set(result)
            return result
        
        return wrapper
    return decorator


# =============================================================
# CACHES PRÉ-CONFIGURADOS (Singleton)
# =============================================================
# Instâncias prontas para uso nos endpoints.
# TTL de 24 horas (1440 min) para dados trimestrais.
# =============================================================
estatisticas_cache: TTLCache[Any] = TTLCache(ttl_minutes=1440, name="estatisticas")
acima_media_cache: TTLCache[Any] = TTLCache(ttl_minutes=1440, name="acima_media")
distribuicao_uf_cache: TTLCache[Any] = TTLCache(ttl_minutes=1440, name="distribuicao_uf")

# Registra caches para observabilidade
CacheRegistry.register(estatisticas_cache)
CacheRegistry.register(acima_media_cache)
CacheRegistry.register(distribuicao_uf_cache)
