# =============================================================
# application/__init__.py - Camada de Aplicação (Use Cases)
# =============================================================
# A camada de APLICAÇÃO contém:
# - Casos de Uso (Interactors): Orquestram o fluxo de dados.
# - Interfaces de Repositório: Contratos abstratos (ABCs).
#
# REGRA: Esta camada conhece APENAS o Domínio.
# - PODE importar de src.domain
# - NÃO importa FastAPI, SQLAlchemy, ou infraestrutura.
#
# Os Use Cases definem O QUE o sistema faz.
# A Infraestrutura define COMO o sistema faz.
# =============================================================
