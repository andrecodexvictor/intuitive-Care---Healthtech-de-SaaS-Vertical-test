# =============================================================
# interface/__init__.py - Camada de Interface (Adaptadores)
# =============================================================
# A camada de INTERFACE conecta a aplicação ao mundo externo:
# - API REST (FastAPI routers)
# - CLI (command line interface)
# - Web UI (se tivesse templates)
#
# COMPONENTES:
# - api/: Routers FastAPI, schemas de request/response
# - cli/: Comandos de terminal (ETL, migrations)
#
# REGRA: Esta camada conhece Application e Domain.
# - PODE importar Use Cases da Application.
# - PODE usar FastAPI, Pydantic schemas.
# - NÃO acessa banco diretamente (usa repositórios).
# =============================================================
