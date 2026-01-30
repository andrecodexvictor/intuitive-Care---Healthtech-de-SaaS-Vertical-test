# =============================================================
# infrastructure/__init__.py - Camada de Infraestrutura
# =============================================================
# A camada de INFRAESTRUTURA contém:
# - Database: Conexão, ORM models, migration.
# - Repositories: Implementação concreta dos contratos.
# - External Services: APIs externas, filas, cache.
# - ETL Agent: Serviço de ingestão de dados.
#
# REGRA: Esta é a camada mais externa.
# - PODE importar de Application e Domain.
# - PODE usar bibliotecas externas (SQLAlchemy, FastAPI, Redis).
# - É a única camada que conhece detalhes de implementação.
# =============================================================
