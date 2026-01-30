# =============================================================
# config.py - Configurações Centralizadas da Aplicação
# =============================================================
# DECISÃO ARQUITETURAL:
# Este arquivo centraliza TODAS as configurações da aplicação.
# Seguindo o princípio do `unifiedConfig` (Backend Dev Guidelines),
# NÃO usamos `os.getenv()` espalhado pelo código.
# Isso facilita testes (mock de config), deploy (variáveis em um lugar)
# e segurança (não expor secrets em logs acidentalmente).
#
# TECNOLOGIA: Pydantic Settings (pydantic-settings)
# - Validação automática de tipos nas variáveis de ambiente.
# - Valores default para desenvolvimento local.
# - Suporte a arquivos `.env` sem bibliotecas extras.
# =============================================================
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas de variáveis de ambiente.
    
    POR QUE PYDANTIC SETTINGS?
    - Type safety: Se DATABASE_URL não for string, falha na inicialização.
    - Validação: Podemos adicionar validators (ex: URL válida).
    - Documentação: Os campos são auto-documentados.
    - Integração com FastAPI: Fácil dependency injection.
    """
    
    # =========================================================
    # Configurações do Banco de Dados (MySQL)
    # =========================================================
    # DECISÃO: MySQL ao invés de PostgreSQL.
    # JUSTIFICATIVA: Maior familiaridade do desenvolvedor.
    # TRADE-OFF: PostgreSQL tem melhor suporte a window functions,
    # mas MySQL 8.0+ já suporta a maioria das features necessárias.
    # =========================================================
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = ""  # Vazio para desenvolvimento local
    DATABASE_NAME: str = "intuitive_care_test"
    
    @property
    def DATABASE_URL(self) -> str:
        """
        Monta a URL de conexão do SQLAlchemy para MySQL.
        
        FORMATO: mysql+pymysql://user:password@host:port/database
        
        DRIVER: PyMySQL
        - Pure Python, não precisa de compilação.
        - Funciona bem em Windows sem configuração extra.
        - Alternativa seria mysqlclient (mais rápido, mas precisa de C compiler).
        """
        return (
            f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            "?charset=utf8mb4"  # Suporte completo a Unicode (emojis, etc.)
        )
    
    # =========================================================
    # Configurações da API
    # =========================================================
    API_TITLE: str = "Intuitive Care - API de Análise de Despesas"
    API_VERSION: str = "1.0.0"
    API_DEBUG: bool = True  # Desativar em produção!
    
    # Paginação padrão
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # =========================================================
    # Configurações de Logging
    # =========================================================
    # DECISÃO: Usar loguru ao invés do logging padrão.
    # JUSTIFICATIVA: API mais simples, output colorido, rotação de arquivos.
    # =========================================================
    LOG_LEVEL: str = "INFO"
    
    # =========================================================
    # Paths de Dados
    # =========================================================
    DATA_DIR: str = "./data"  # Diretório para arquivos baixados/gerados
    
    # =========================================================
    # Configuração do Pydantic Settings
    # =========================================================
    model_config = SettingsConfigDict(
        env_file=".env",  # Carrega variáveis de arquivo .env se existir
        env_file_encoding="utf-8",
        case_sensitive=True,  # DATABASE_HOST != database_host
        extra="ignore",  # Ignora variáveis extras no .env
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações.
    
    POR QUE LRU_CACHE?
    - Evita recarregar o arquivo .env a cada chamada.
    - A instância é criada uma vez e reutilizada.
    - Em testes, podemos limpar o cache: get_settings.cache_clear()
    """
    return Settings()


# Exporta instância global para uso direto
# Uso: from src.config import settings
settings = get_settings()
