# =============================================================
# operadoras.py - Router para Endpoints de Operadoras
# =============================================================
# ARQUITETURA: Clean Architecture - Interface Layer (Adapter)
#
# RESPONSABILIDADES DO ROUTER:
# 1. Definir endpoints HTTP (rotas).
# 2. Validar request (via Pydantic schemas).
# 3. Chamar repositórios/use cases.
# 4. Formatar response.
#
# O ROUTER NÃO DEVE:
# - Ter lógica de negócio complexa.
# - Acessar banco diretamente (usa repositório).
# - Fazer cálculos que deveriam estar em Use Cases.
# =============================================================
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from src.config import settings
from src.infrastructure.database.connection import get_db
from src.infrastructure.database.repositories import (
    OperadoraRepository,
    DespesaRepository,
)
from src.interface.api.schemas import (
    OperadoraResponse,
    OperadoraDetalheResponse,
    DespesaResponse,
    PaginatedResponse,
    ErrorResponse,
)


# =============================================================
# CRIAÇÃO DO ROUTER
# =============================================================
# prefix: Todas as rotas começam com /api/operadoras
# tags: Agrupa no Swagger UI
# responses: Define respostas de erro padrão
# =============================================================
router = APIRouter(
    prefix="/api/operadoras",
    tags=["Operadoras"],
    responses={
        404: {"model": ErrorResponse, "description": "Operadora não encontrada"},
        500: {"model": ErrorResponse, "description": "Erro interno do servidor"},
    },
)


# =============================================================
# GET /api/operadoras - Lista com paginação e filtros
# =============================================================
@router.get(
    "",
    response_model=PaginatedResponse[OperadoraResponse],
    summary="Lista operadoras com paginação",
    description="""
    Retorna lista paginada de operadoras de plano de saúde.
    
    **Paginação:**
    - `page`: Número da página (começando em 1)
    - `limit`: Quantidade de itens por página (máx. 100)
    
    **Filtros opcionais:**
    - `razao_social`: Busca por nome (case-insensitive, parcial)
    - `cnpj`: Busca por CNPJ (parcial)
    
    **Exemplo:**
    ```
    GET /api/operadoras?page=1&limit=20&razao_social=UNIMED
    ```
    """,
)
async def listar_operadoras(
    page: int = Query(default=1, ge=1, description="Número da página"),
    limit: int = Query(
        default=settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description="Items por página",
    ),
    razao_social: Optional[str] = Query(
        default=None,
        description="Filtro por razão social (parcial, case-insensitive)",
    ),
    cnpj: Optional[str] = Query(
        default=None,
        description="Filtro por CNPJ (parcial)",
    ),
    db: Session = Depends(get_db),
):
    """
    Lista operadoras com paginação offset-based.
    
    DECISÃO: Offset-based pagination ao invés de cursor-based.
    JUSTIFICATIVA:
    - Dados relativamente estáticos (atualizados trimestralmente).
    - ~5000 operadoras = volume gerenciável para offset.
    - Simplicidade: frontend sabe total de páginas.
    
    TRADE-OFF:
    - Cursor seria melhor para dados muito dinâmicos.
    - Offset fica lento com milhões de registros.
    """
    repo = OperadoraRepository(db)
    operadoras, total = await repo.list_all(
        page=page,
        limit=limit,
        razao_social_filter=razao_social,
        cnpj_filter=cnpj,
    )
    
    return PaginatedResponse(
        data=[OperadoraResponse.model_validate(o) for o in operadoras],
        total=total,
        page=page,
        limit=limit,
    )


# =============================================================
# GET /api/operadoras/{cnpj} - Detalhes de uma operadora
# =============================================================
@router.get(
    "/{cnpj}",
    response_model=OperadoraDetalheResponse,
    summary="Obtém detalhes de uma operadora",
    description="""
    Retorna informações detalhadas de uma operadora específica.
    
    **Parâmetro:**
    - `cnpj`: CNPJ da operadora (14 dígitos, sem formatação)
    
    **Retorna:**
    - Dados cadastrais
    - Total de despesas acumuladas
    - Quantidade de trimestres com dados
    """,
    responses={
        404: {"model": ErrorResponse, "description": "Operadora não encontrada"},
    },
)
async def obter_operadora(
    cnpj: str,
    db: Session = Depends(get_db),
):
    """
    Busca operadora por CNPJ.
    
    VALIDAÇÃO:
    O CNPJ é validado implicitamente pelo repositório.
    Se não encontrado, retorna 404.
    
    DECISÃO: Não validar formato do CNPJ no router.
    JUSTIFICATIVA:
    - Mesmo CNPJ inválido pode existir no banco (dados legados).
    - Validação detalhada é feita na ingestão (ETL).
    - Aqui, simplesmente buscamos pelo valor informado.
    """
    repo = OperadoraRepository(db)
    operadora = await repo.get_by_cnpj(cnpj)
    
    if operadora is None:
        raise HTTPException(
            status_code=404,
            detail=f"Operadora com CNPJ {cnpj} não encontrada",
        )
    
    # Busca despesas para calcular totais
    despesa_repo = DespesaRepository(db)
    despesas = await despesa_repo.get_by_operadora(cnpj)
    
    total_despesas = sum(d.valor for d in despesas)
    quantidade_trimestres = len(set((d.ano, d.trimestre) for d in despesas))
    
    return OperadoraDetalheResponse(
        cnpj=operadora.cnpj,
        razao_social=operadora.razao_social,
        registro_ans=operadora.registro_ans,
        modalidade=operadora.modalidade.value if operadora.modalidade else None,
        uf=operadora.uf,
        total_despesas=total_despesas,
        quantidade_trimestres=quantidade_trimestres,
    )


# =============================================================
# GET /api/operadoras/{cnpj}/despesas - Histórico de despesas
# =============================================================
@router.get(
    "/{cnpj}/despesas",
    response_model=List[DespesaResponse],
    summary="Histórico de despesas de uma operadora",
    description="""
    Retorna o histórico de despesas de uma operadora.
    
    **Parâmetros opcionais:**
    - `ano`: Filtrar por ano específico
    - `trimestre`: Filtrar por trimestre (1-4)
    
    **Ordenação:**
    Resultados ordenados por período (mais recente primeiro).
    """,
)
async def listar_despesas_operadora(
    cnpj: str,
    ano: Optional[int] = Query(default=None, ge=2000, le=2100, description="Filtrar por ano"),
    trimestre: Optional[int] = Query(default=None, ge=1, le=4, description="Filtrar por trimestre"),
    db: Session = Depends(get_db),
):
    """
    Lista despesas de uma operadora.
    
    ORDENAÇÃO:
    Dados mais recentes primeiro (DESC por ano, trimestre).
    Isso facilita visualização no frontend.
    """
    # Verifica se operadora existe
    op_repo = OperadoraRepository(db)
    operadora = await op_repo.get_by_cnpj(cnpj)
    
    if operadora is None:
        raise HTTPException(
            status_code=404,
            detail=f"Operadora com CNPJ {cnpj} não encontrada",
        )
    
    # Busca despesas
    despesa_repo = DespesaRepository(db)
    despesas = await despesa_repo.get_by_operadora(
        cnpj=cnpj,
        ano=ano,
        trimestre=trimestre,
    )
    
    return [DespesaResponse.model_validate(d) for d in despesas]
