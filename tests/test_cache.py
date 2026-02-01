# =============================================================
# test_cache.py - Testes Unitários do Sistema de Cache
# =============================================================
# Cobertura: TTLCache, CacheRegistry, decorator @cached
#
# TESTES:
# - Armazenamento e recuperação de dados
# - Expiração baseada em TTL
# - Thread-safety
# - Estatísticas de hit/miss
# - Invalidação de cache
# =============================================================
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import threading
import time

from src.infrastructure.cache import (
    TTLCache,
    CacheRegistry,
    cached,
    estatisticas_cache,
    acima_media_cache,
)


class TestTTLCache:
    """Testes da classe TTLCache genérica."""
    
    def test_set_and_get_basic(self):
        """Cache deve armazenar e recuperar dados corretamente."""
        cache = TTLCache[dict](ttl_minutes=15, name="test_basic")
        
        data = {"total": 1000, "items": [1, 2, 3]}
        cache.set(data)
        
        result = cache.get()
        assert result == data
        assert result["total"] == 1000
    
    def test_get_returns_none_when_empty(self):
        """Cache vazio deve retornar None."""
        cache = TTLCache[str](ttl_minutes=15, name="test_empty")
        
        result = cache.get()
        assert result is None
    
    def test_cache_expiration(self):
        """Cache deve expirar após TTL."""
        cache = TTLCache[str](ttl_minutes=1, name="test_expiration")
        cache.set("test_data")
        
        # Simula passagem do tempo manipulando timestamp
        cache._timestamp = datetime.now() - timedelta(minutes=2)
        
        result = cache.get()
        assert result is None
    
    def test_cache_valid_before_expiration(self):
        """Cache deve ser válido antes do TTL."""
        cache = TTLCache[str](ttl_minutes=60, name="test_valid")
        cache.set("test_data")
        
        # Simula 30 minutos (ainda dentro do TTL de 60 min)
        cache._timestamp = datetime.now() - timedelta(minutes=30)
        
        result = cache.get()
        assert result == "test_data"
    
    def test_invalidate_clears_cache(self):
        """Invalidação deve limpar dados e timestamp."""
        cache = TTLCache[dict](ttl_minutes=15, name="test_invalidate")
        cache.set({"key": "value"})
        
        cache.invalidate()
        
        assert cache.get() is None
        assert cache._data is None
        assert cache._timestamp is None
    
    def test_stats_tracking(self):
        """Estatísticas devem rastrear hits e misses."""
        cache = TTLCache[int](ttl_minutes=15, name="test_stats")
        
        # 2 misses
        cache.get()
        cache.get()
        
        # Set data
        cache.set(42)
        
        # 3 hits
        cache.get()
        cache.get()
        cache.get()
        
        stats = cache.stats
        assert stats["hits"] == 3
        assert stats["misses"] == 2
        assert stats["total_requests"] == 5
        assert stats["hit_rate_percent"] == 60.0
    
    def test_stats_with_zero_requests(self):
        """Estatísticas com zero requisições não deve dividir por zero."""
        cache = TTLCache[str](ttl_minutes=15, name="test_zero")
        
        stats = cache.stats
        assert stats["hit_rate_percent"] == 0
        assert stats["total_requests"] == 0
    
    def test_thread_safety(self):
        """Cache deve ser thread-safe."""
        cache = TTLCache[int](ttl_minutes=15, name="test_thread")
        results = []
        errors = []
        
        def writer():
            try:
                for i in range(100):
                    cache.set(i)
            except Exception as e:
                errors.append(e)
        
        def reader():
            try:
                for _ in range(100):
                    result = cache.get()
                    if result is not None:
                        results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread errors: {errors}"
    
    def test_repr_string(self):
        """__repr__ deve retornar string informativa."""
        cache = TTLCache[str](ttl_minutes=15, name="test_repr")
        
        repr_str = repr(cache)
        assert "test_repr" in repr_str
        assert "TTLCache" in repr_str
    
    def test_generic_types(self):
        """Cache deve funcionar com diferentes tipos."""
        # String
        str_cache = TTLCache[str](ttl_minutes=1, name="str")
        str_cache.set("hello")
        assert str_cache.get() == "hello"
        
        # List
        list_cache = TTLCache[list](ttl_minutes=1, name="list")
        list_cache.set([1, 2, 3])
        assert list_cache.get() == [1, 2, 3]
        
        # Dict
        dict_cache = TTLCache[dict](ttl_minutes=1, name="dict")
        dict_cache.set({"a": 1})
        assert dict_cache.get() == {"a": 1}


class TestCacheRegistry:
    """Testes do registro centralizado de caches."""
    
    def test_register_and_get_stats(self):
        """Registry deve registrar caches e retornar estatísticas."""
        # Caches já registrados no módulo
        stats = CacheRegistry.get_all_stats()
        
        assert isinstance(stats, list)
        assert len(stats) >= 3  # estatisticas, acima_media, distribuicao_uf
        
        # Verifica estrutura das estatísticas
        for stat in stats:
            assert "name" in stat
            assert "hits" in stat
            assert "misses" in stat
            assert "hit_rate_percent" in stat
    
    def test_invalidate_all(self):
        """Invalidar todos deve limpar todos os caches registrados."""
        # Set some data
        estatisticas_cache.set({"test": True})
        acima_media_cache.set([{"test": True}])
        
        # Invalidate all
        CacheRegistry.invalidate_all()
        
        # Verify
        assert estatisticas_cache.get() is None
        assert acima_media_cache.get() is None


class TestCachedDecorator:
    """Testes do decorator @cached."""
    
    def test_decorator_caches_result(self):
        """Decorator deve cachear resultado da função."""
        cache = TTLCache[int](ttl_minutes=15, name="test_decorator")
        call_count = 0
        
        @cached(cache)
        def expensive_function():
            nonlocal call_count
            call_count += 1
            return 42
        
        # Primeira chamada - executa função
        result1 = expensive_function()
        assert result1 == 42
        assert call_count == 1
        
        # Segunda chamada - usa cache
        result2 = expensive_function()
        assert result2 == 42
        assert call_count == 1  # Não incrementou
    
    def test_decorator_returns_fresh_after_expiration(self):
        """Decorator deve recalcular após expiração."""
        cache = TTLCache[str](ttl_minutes=1, name="test_decorator_expire")
        call_count = 0
        
        @cached(cache)
        def get_timestamp():
            nonlocal call_count
            call_count += 1
            return f"call_{call_count}"
        
        # Primeira chamada
        result1 = get_timestamp()
        assert result1 == "call_1"
        
        # Expira cache
        cache._timestamp = datetime.now() - timedelta(minutes=5)
        
        # Segunda chamada - recalcula
        result2 = get_timestamp()
        assert result2 == "call_2"
        assert call_count == 2


class TestPreConfiguredCaches:
    """Testes dos caches pré-configurados."""
    
    def test_estatisticas_cache_exists(self):
        """Cache de estatísticas deve estar configurado."""
        assert estatisticas_cache is not None
        assert estatisticas_cache._name == "estatisticas"
        assert estatisticas_cache._ttl == timedelta(minutes=1440)  # 24h
    
    def test_acima_media_cache_exists(self):
        """Cache de acima_media deve estar configurado."""
        assert acima_media_cache is not None
        assert acima_media_cache._name == "acima_media"
    
    def test_caches_are_registered(self):
        """Caches pré-configurados devem estar no registry."""
        stats = CacheRegistry.get_all_stats()
        names = [s["name"] for s in stats]
        
        assert "estatisticas" in names
        assert "acima_media" in names
        assert "distribuicao_uf" in names
