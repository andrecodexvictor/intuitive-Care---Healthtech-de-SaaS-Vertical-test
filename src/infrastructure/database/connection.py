# =============================================================
# connection.py - Conexão com Banco de Dados (SQLAlchemy)
# =============================================================
# ARQUITETURA: Clean Architecture - Infraestrutura
#
# TECNOLOGIAS:
# - SQLAlchemy 2.0: ORM maduro, suporta async, type hints.
# - PyMySQL: Driver MySQL pure Python (fácil instalação Windows).
#
# PADRÃO: Session per Request
# - Cada requisição HTTP recebe uma session.
# - Session é fechada ao final da requisição (via dependency).
# - Evita connection exhaustion e memory leaks.
# =============================================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base  # Legacy import for SQLAlchemy < 2.0
from src.config import settings


# =============================================================
# BASE DECLARATIVA
# =============================================================
# Todas as ORM models herdam desta base.
# Isso permite que o SQLAlchemy conheça todas as tabelas.
#
# NOTA: Usando declarative_base() para compatibilidade com Python 3.9+
# SQLAlchemy 2.0 DeclarativeBase requer Python 3.10+
# =============================================================
Base = declarative_base()



# =============================================================
# ENGINE DE CONEXÃO
# =============================================================
# CONFIGURAÇÕES IMPORTANTES:
# - pool_size: Conexões mantidas abertas permanentemente.
# - max_overflow: Conexões extras em picos de demanda.
# - pool_recycle: Tempo máximo de vida de uma conexão (MySQL timeout).
# - echo: Loga todas as queries SQL (útil para debug).
# =============================================================
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,  # 5 conexões base
    max_overflow=10,  # Até 15 conexões no pico
    pool_recycle=3600,  # Recicla conexão a cada 1h (evita timeout MySQL)
    echo=settings.API_DEBUG,  # Em debug, mostra SQL no console
)


# =============================================================
# SESSION FACTORY
# =============================================================
# SessionLocal é uma "fábrica de sessions".
# Cada chamada a SessionLocal() cria uma nova session.
#
# CONFIGURAÇÕES:
# - autocommit=False: Requer commit explícito (transações manuais).
# - autoflush=False: Não sincroniza automaticamente (melhor performance).
# - expire_on_commit=False: Objetos permanecem usáveis após commit.
# =============================================================
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Session:
    """
    Dependency para FastAPI que fornece uma session do banco.
    
    USO NO FASTAPI:
    ```python
    @app.get("/operadoras")
    def listar(db: Session = Depends(get_db)):
        # usa db aqui
        ...
    ```
    
    O yield garante que a session é fechada mesmo se houver erro.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Cria todas as tabelas definidas nos ORM models.
    
    CUIDADO: Só execute em ambiente de desenvolvimento.
    Em produção, use migrations (Alembic).
    """
    Base.metadata.create_all(bind=engine)
