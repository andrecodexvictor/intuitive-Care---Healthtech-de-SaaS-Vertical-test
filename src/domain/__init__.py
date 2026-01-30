# =============================================================
# domain/__init__.py - Camada de Domínio (Clean Architecture)
# =============================================================
# A camada de DOMÍNIO contém:
# - Entidades: Objetos de negócio com identidade (ex: Operadora, Despesa)
# - Value Objects: Objetos sem identidade (ex: CNPJ, Periodo)
# - Regras de negócio puras (validações, cálculos)
#
# REGRA DE OURO: Esta camada NÃO CONHECE nenhuma outra.
# - NÃO importa FastAPI
# - NÃO importa SQLAlchemy
# - NÃO importa bibliotecas de infraestrutura
#
# Isso garante que a lógica de negócio é testável e portátil.
# =============================================================
