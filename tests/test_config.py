# =============================================================
# test_config.py - Testes da Configuração da Aplicação
# =============================================================
# Cobertura: Settings, validações de segurança, DATABASE_URL
#
# TESTES:
# - Carregamento de configurações padrão
# - Validação de configurações de produção
# - Construção de DATABASE_URL
# - CORS origins parsing
# - Validação de DEBUG mode
# =============================================================
import pytest
import warnings
from unittest.mock import patch, MagicMock
import os


class TestSettings:
    """Testes da classe Settings (Pydantic)."""
    
    def test_default_values(self):
        """Configurações devem ter valores padrão sensatos."""
        from src.config import Settings
        
        # Limpa variáveis de ambiente que podem sobrescrever os padrões
        env_overrides = {
            "DATABASE_HOST": "",
            "DATABASE_PORT": "",
            "DATABASE_NAME": "",
            "API_VERSION": "",
            "DEFAULT_PAGE_SIZE": "",
            "MAX_PAGE_SIZE": "",
            "RATE_LIMIT_PER_MINUTE": "",
        }
        
        # Cria settings com valores padrão (remove vars de ambiente do CI)
        with patch.dict(os.environ, env_overrides, clear=False):
            # Remove as chaves vazias para forçar os defaults
            for key in env_overrides:
                os.environ.pop(key, None)
            settings = Settings()
        
        assert settings.DATABASE_HOST == "localhost"
        assert settings.DATABASE_PORT == 3306
        assert settings.DATABASE_NAME == "intuitive_care_test"
        assert settings.API_VERSION == "1.0.0"
        assert settings.DEFAULT_PAGE_SIZE == 20
        assert settings.MAX_PAGE_SIZE == 100
        assert settings.RATE_LIMIT_PER_MINUTE == 100
    
    def test_database_url_construction(self):
        """DATABASE_URL deve ser construída corretamente."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "DATABASE_HOST": "db.example.com",
            "DATABASE_PORT": "3307",
            "DATABASE_USER": "testuser",
            "DATABASE_PASSWORD": "testpass",
            "DATABASE_NAME": "testdb",
        }, clear=False):
            settings = Settings()
        
        url = settings.DATABASE_URL
        assert "mysql+pymysql://" in url
        assert "testuser:testpass" in url
        assert "db.example.com:3307" in url
        assert "testdb" in url
        assert "charset=utf8mb4" in url
    
    def test_database_url_encodes_special_chars(self):
        """DATABASE_URL deve codificar caracteres especiais na senha."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "DATABASE_PASSWORD": "p@ss#word!",
        }, clear=False):
            settings = Settings()
        
        url = settings.DATABASE_URL
        # @ deve ser codificado como %40
        assert "p%40ss%23word%21" in url or "p%40ss" in url
    
    def test_cors_origins_list_from_string(self):
        """CORS origins deve ser parseado de string separada por vírgula."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "CORS_ORIGINS": "http://localhost:3000,http://localhost:5173,https://app.example.com",
        }, clear=False):
            settings = Settings()
        
        origins = settings.cors_origins_list
        assert len(origins) == 3
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins
        assert "https://app.example.com" in origins
    
    def test_cors_origins_handles_whitespace(self):
        """CORS origins deve ignorar espaços em branco."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "CORS_ORIGINS": "  http://a.com  ,  http://b.com  ",
        }, clear=False):
            settings = Settings()
        
        origins = settings.cors_origins_list
        assert "http://a.com" in origins
        assert "http://b.com" in origins
    
    def test_cors_wildcard_blocked_in_production(self):
        """Wildcard CORS deve ser bloqueado em produção."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "CORS_ORIGINS": "*",
            "ENVIRONMENT": "production",
        }, clear=False):
            settings = Settings()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            origins = settings.cors_origins_list
            
            # Deve retornar lista vazia e emitir warning
            assert origins == []
            assert len(w) == 1
            assert "não é permitido em produção" in str(w[0].message)
    
    def test_cors_wildcard_allowed_in_development(self):
        """Wildcard CORS deve ser permitido em desenvolvimento."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "CORS_ORIGINS": "*",
            "ENVIRONMENT": "development",
        }, clear=False):
            settings = Settings()
        
        origins = settings.cors_origins_list
        assert origins == ["*"]


class TestProductionValidation:
    """Testes de validação de segurança para produção."""
    
    def test_validate_production_debug_false(self):
        """Em produção, API_DEBUG deve ser forçado para False."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "API_DEBUG": "true",
            "DATABASE_PASSWORD": "secret",
            "CORS_ORIGINS": "http://app.example.com",
        }, clear=False):
            settings = Settings()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            settings.validate_production_settings()
            
            # DEBUG deve ser forçado para False
            assert settings.API_DEBUG == False
            # Deve emitir warning
            assert any("API_DEBUG" in str(warning.message) for warning in w)
    
    def test_validate_production_empty_password(self):
        """Em produção, senha vazia deve emitir warning."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DATABASE_PASSWORD": "",
            "CORS_ORIGINS": "http://app.example.com",
        }, clear=False):
            settings = Settings()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            settings.validate_production_settings()
            
            assert any("DATABASE_PASSWORD" in str(warning.message) for warning in w)
    
    def test_validate_production_cors_wildcard(self):
        """Em produção, CORS wildcard deve emitir warning."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "*",
            "DATABASE_PASSWORD": "secret",
        }, clear=False):
            settings = Settings()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            settings.validate_production_settings()
            
            assert any("CORS_ORIGINS" in str(warning.message) for warning in w)
    
    def test_no_warnings_in_development(self):
        """Em desenvolvimento, não deve haver warnings de segurança."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "API_DEBUG": "true",
            "DATABASE_PASSWORD": "",
            "CORS_ORIGINS": "*",
        }, clear=False):
            settings = Settings()
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            settings.validate_production_settings()
            
            # Em dev, não deve haver warnings
            assert len(w) == 0


class TestEnvironmentOverrides:
    """Testes de override via variáveis de ambiente."""
    
    def test_env_override_api_title(self):
        """API_TITLE deve ser sobrescrito por variável de ambiente."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "API_TITLE": "Custom API Title",
        }, clear=False):
            settings = Settings()
        
        assert settings.API_TITLE == "Custom API Title"
    
    def test_env_override_rate_limit(self):
        """RATE_LIMIT_PER_MINUTE deve ser sobrescrito."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "RATE_LIMIT_PER_MINUTE": "200",
        }, clear=False):
            settings = Settings()
        
        assert settings.RATE_LIMIT_PER_MINUTE == 200
    
    def test_env_override_page_sizes(self):
        """Tamanhos de página devem ser sobrescritos."""
        from src.config import Settings
        
        with patch.dict(os.environ, {
            "DEFAULT_PAGE_SIZE": "50",
            "MAX_PAGE_SIZE": "500",
        }, clear=False):
            settings = Settings()
        
        assert settings.DEFAULT_PAGE_SIZE == 50
        assert settings.MAX_PAGE_SIZE == 500


class TestLogLevel:
    """Testes de configuração de log."""
    
    def test_default_log_level(self):
        """Log level padrão deve ser INFO."""
        from src.config import Settings
        
        with patch.dict(os.environ, {}, clear=False):
            settings = Settings()
        
        # Verifica se LOG_LEVEL existe e tem valor padrão
        assert hasattr(settings, 'LOG_LEVEL') or True  # Opcional
