# =============================================================
# estatisticas.py - Router para Endpoints de Estatísticas
# =============================================================
# ARQUITETURA: Clean Architecture - Interface Layer
#
# Este router agrupa endpoints de agregação e analytics.
# São queries mais pesadas, então implementamos cache.
# =============================================================
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from functools import lru_cache
from datetime import datetime, timedelta
from typing import List

from src.infrastructure.database.connection import get_db
from src.infrastructure.database.repositories import DespesaRepository
from src.infrastructure.database.models import DespesaORM, OperadoraORM
from src.interface.api.schemas import (
    EstatisticasResponse,
    TopOperadoraResponse,
    DistribuicaoUFResponse,
)


router = APIRouter(
    prefix="/api/estatisticas",
    tags=["Estatísticas"],
)


# =============================================================
# CACHE DE ESTATÍSTICAS
# =============================================================
# DECISÃO: Usar cache em memória (lru_cache) para estatísticas.
# JUSTIFICATIVA:
# - Query de agregação é custosa (processa milhares de registros).
# - Dados atualizados trimestralmente (não precisa real-time).
# - Cache de 15 minutos é suficiente.
#
# TRADE-OFF:
# - Em produção com múltiplas instâncias, usaríamos Redis.
# - lru_cache funciona apenas em processo único.
# - Para este protótipo, é suficiente.
#
# IMPLEMENTAÇÃO:
# - Cache com timestamp (invalida após 15 min).
# - Simples mas efetivo para MVP.
# =============================================================
_cache_estatisticas = None
_cache_timestamp = None
CACHE_TTL_MINUTES = 15


def get_cached_estatisticas():
    """Retorna estatísticas cacheadas ou None se expirado."""
    global _cache_estatisticas, _cache_timestamp
    
    if _cache_estatisticas is None:
        return None
    
    if datetime.now() - _cache_timestamp > timedelta(minutes=CACHE_TTL_MINUTES):
        _cache_estatisticas = None
        return None
    
    return _cache_estatisticas


def set_cached_estatisticas(data):
    """Armazena estatísticas no cache."""
    global _cache_estatisticas, _cache_timestamp
    _cache_estatisticas = data
    _cache_timestamp = datetime.now()


# =============================================================
# GET /api/estatisticas - Estatísticas gerais
# =============================================================
@router.get(
    "",
    response_model=EstatisticasResponse,
    summary="Estatísticas agregadas de despesas",
    description="""
    Retorna estatísticas agregadas de todas as despesas.
    
    **Inclui:**
    - Total geral de despesas
    - Média por registro
    - Quantidade total de registros
    - Top 5 operadoras com maiores despesas
    
    **Cache:**
    Resultados são cacheados por 15 minutos para melhor performance.
    """,
)
async def obter_estatisticas(
    db: Session = Depends(get_db),
):
    """
    Calcula estatísticas gerais de despesas.
    
    PERFORMANCE:
    - Query agrega todos os registros (pode ser lenta).
    - Cache de 15 min evita recálculo desnecessário.
    
    DECISÃO: Calcular na hora (com cache) ao invés de pré-calcular.
    JUSTIFICATIVA:
    - Dados mudam apenas na ingestão (uma vez por trimestre).
    - Pré-calcular adicionaria complexidade (tabela materializada).
    - Cache simples resolve para este volume (~10K registros).
    """
    # Tenta cache primeiro
    cached = get_cached_estatisticas()
    if cached:
        return cached
    
    # Calcula estatísticas
    repo = DespesaRepository(db)
    stats = await repo.get_estatisticas_gerais()
    
    result = EstatisticasResponse(
        total_despesas=stats["total_despesas"],
        media_despesas=stats["media_despesas"],
        quantidade_registros=stats["quantidade_registros"],
        top_5_operadoras=[
            TopOperadoraResponse(**op) for op in stats["top_5_operadoras"]
        ],
    )
    
    # Armazena no cache
    set_cached_estatisticas(result)
    
    return result


# =============================================================
# GET /api/estatisticas/distribuicao-uf - Por estado
# =============================================================
@router.get(
    "/distribuicao-uf",
    response_model=List[DistribuicaoUFResponse],
    summary="Distribuição de despesas por UF",
    description="""
    Retorna a distribuição de despesas por UF (estado).
    
    Útil para gráficos de pizza/barra no frontend.
    
    **Ordenação:** Por total de despesas (maior primeiro).
    """,
)
async def obter_distribuicao_uf(
    db: Session = Depends(get_db),
):
    """
    Calcula distribuição de despesas por UF.
    
    QUERY:
    SELECT uf, SUM(valor) as total
    FROM despesas d
    JOIN operadoras o ON d.cnpj = o.cnpj
    GROUP BY uf
    ORDER BY total DESC
    """
    # Query com JOIN para pegar UF da operadora
    results = (
        db.query(
            OperadoraORM.uf,
            func.sum(DespesaORM.valor).label("total"),
        )
        .join(DespesaORM, OperadoraORM.cnpj == DespesaORM.cnpj)
        .group_by(OperadoraORM.uf)
        .order_by(desc(func.sum(DespesaORM.valor)))
        .all()
    )
    
    # Calcula total geral para percentuais
    total_geral = sum(r.total for r in results if r.total)
    
    return [
        DistribuicaoUFResponse(
            uf=r.uf or "N/A",
            total=float(r.total or 0),
            percentual=round((r.total / total_geral * 100) if total_geral else 0, 2),
        )
        for r in results
    ]
