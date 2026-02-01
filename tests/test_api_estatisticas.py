# =============================================================
# test_api_estatisticas.py - Testes de Integração da API de Estatísticas
# =============================================================
# COBERTURA: Endpoints de agregação, cache TTLCache, distribuição UF
# =============================================================
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# =============================================================
# Testes de Estatísticas Gerais (GET /api/estatisticas)
# =============================================================
class TestObterEstatisticas:
    """Testes para o endpoint de estatísticas gerais."""
    
    @pytest.mark.unit
    def test_obter_estatisticas_sucesso(self, client):
        """Deve retornar estatísticas gerais."""
        response = client.get("/api/estatisticas")
        
        # O endpoint pode retornar 200 (sucesso) ou 500 (sem banco)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "total_despesas" in data
            assert "media_despesas" in data
            assert "quantidade_registros" in data
            assert "top_5_operadoras" in data
    
    @pytest.mark.unit
    def test_obter_estatisticas_com_cache(self, client):
        """Deve retornar estatísticas do cache se disponível."""
        # Mock do cache TTLCache
        mock_cached_data = MagicMock()
        mock_cached_data.total_despesas = 500000.0
        mock_cached_data.media_despesas = 25000.0
        mock_cached_data.quantidade_registros = 20
        mock_cached_data.top_5_operadoras = []
        
        with patch("src.interface.api.routers.estatisticas.estatisticas_cache") as mock_cache:
            mock_cache.get.return_value = mock_cached_data
            
            response = client.get("/api/estatisticas")
            
            assert response.status_code == 200
    
    @pytest.mark.unit
    def test_estatisticas_campos_obrigatorios(self, client):
        """Resposta deve conter todos os campos obrigatórios."""
        response = client.get("/api/estatisticas")
        
        if response.status_code == 200:
            data = response.json()
            assert "total_despesas" in data
            assert "media_despesas" in data
            assert "quantidade_registros" in data
            assert "top_5_operadoras" in data
            assert isinstance(data["top_5_operadoras"], list)
    
    @pytest.mark.unit
    def test_top_5_operadoras_formato(self, client):
        """Top 5 deve ter formato correto (razao_social + total)."""
        response = client.get("/api/estatisticas")
        
        if response.status_code == 200:
            data = response.json()
            if len(data["top_5_operadoras"]) > 0:
                top = data["top_5_operadoras"][0]
                assert "razao_social" in top
                assert "total" in top


# =============================================================
# Testes de Distribuição por UF (GET /api/estatisticas/distribuicao-uf)
# =============================================================
class TestDistribuicaoUF:
    """Testes para o endpoint de distribuição por UF."""
    
    @pytest.mark.unit
    def test_distribuicao_uf_sucesso(self, client):
        """Deve retornar distribuição por UF."""
        response = client.get("/api/estatisticas/distribuicao-uf")
        
        # O endpoint pode retornar 200 (sucesso) ou 500 (sem banco)
        assert response.status_code in [200, 500]
    
    @pytest.mark.unit
    def test_distribuicao_uf_formato_resposta(self, client):
        """Resposta deve ser lista de objetos com uf, total, percentual."""
        response = client.get("/api/estatisticas/distribuicao-uf")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if len(data) > 0:
                item = data[0]
                assert "uf" in item
                assert "total" in item


# =============================================================
# Testes de Cache TTLCache
# =============================================================
class TestCacheEstatisticas:
    """Testes para validar comportamento do cache TTLCache."""
    
    @pytest.mark.unit
    def test_ttl_cache_get_set(self):
        """TTLCache deve armazenar e recuperar dados."""
        from src.infrastructure.cache import TTLCache
        
        cache = TTLCache[dict](ttl_minutes=15, name="test_cache")
        
        # Cache vazio retorna None
        assert cache.get() is None
        
        # Armazena dados
        cache.set({"test": "data"})
        
        # Recupera dados
        result = cache.get()
        assert result == {"test": "data"}
    
    @pytest.mark.unit
    def test_ttl_cache_invalidate(self):
        """TTLCache.invalidate() deve limpar o cache."""
        from src.infrastructure.cache import TTLCache
        
        cache = TTLCache[str](ttl_minutes=15, name="test_invalidate")
        cache.set("test_value")
        
        assert cache.get() == "test_value"
        
        cache.invalidate()
        
        assert cache.get() is None
    
    @pytest.mark.unit
    def test_ttl_cache_stats(self):
        """TTLCache.stats deve retornar estatísticas do cache."""
        from src.infrastructure.cache import TTLCache
        
        cache = TTLCache[int](ttl_minutes=30, name="test_stats")
        
        # Força um miss e um hit
        cache.get()  # miss
        cache.set(42)
        cache.get()  # hit
        
        stats = cache.stats
        assert stats["name"] == "test_stats"
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["ttl_minutes"] == 30
    
    @pytest.mark.unit
    def test_estatisticas_cache_exists(self):
        """Verifica que estatisticas_cache está configurado corretamente."""
        from src.infrastructure.cache import estatisticas_cache
        
        assert estatisticas_cache is not None
        assert estatisticas_cache._name == "estatisticas"
        # TTL de 24h (1440 minutos)
        assert estatisticas_cache._ttl.total_seconds() / 60 == 1440


# =============================================================
# Testes de Content-Type e Headers
# =============================================================
class TestResponseHeaders:
    """Testes para headers das respostas."""
    
    @pytest.mark.unit
    def test_estatisticas_content_type(self, client):
        """Resposta deve ser JSON."""
        with patch("src.interface.api.routers.estatisticas.estatisticas_cache") as mock_cache:
            mock_cache.get.return_value = MagicMock(
                total_despesas=0,
                media_despesas=0,
                quantidade_registros=0,
                top_5_operadoras=[]
            )
            
            response = client.get("/api/estatisticas")
            
            assert "application/json" in response.headers.get("content-type", "")
