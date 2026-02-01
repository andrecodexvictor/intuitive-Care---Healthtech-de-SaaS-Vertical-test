from __future__ import annotations
# schemas.py - API Request/Response contracts
# Separados das entities para maior flexibilidade no versionamento
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# =============================================================
# SCHEMAS DE OPERADORA
# =============================================================
class OperadoraResponse(BaseModel):
    """Response schema para dados de operadora."""
    cnpj: str = Field(..., description="CNPJ da operadora (14 dígitos)")
    razao_social: str = Field(..., description="Nome oficial da operadora")
    registro_ans: Optional[str] = Field(None, description="Registro na ANS (6 dígitos)")
    modalidade: Optional[str] = Field(None, description="Modalidade de operação")
    uf: Optional[str] = Field(None, description="UF da sede")
    
    class Config:
        from_attributes = True  # Permite criar de ORM models


class OperadoraDetalheResponse(OperadoraResponse):
    """
    Schema de resposta com detalhes completos da operadora.
    
    Inclui estatísticas calculadas e lista de despesas.
    """
    total_despesas: float = Field(default=0.0, description="Total de despesas acumuladas")
    quantidade_trimestres: int = Field(default=0, description="Quantidade de trimestres com dados")


# =============================================================
# SCHEMAS DE DESPESA
# =============================================================
class DespesaResponse(BaseModel):
    """
    Schema de resposta para uma despesa financeira.
    """
    id: Optional[int] = Field(None, description="ID interno")
    cnpj: str = Field(..., description="CNPJ da operadora")
    ano: int = Field(..., description="Ano do registro")
    trimestre: int = Field(..., description="Trimestre (1-4)")
    valor: float = Field(..., description="Valor em R$")
    status_qualidade: str = Field(default="OK", description="Status de qualidade do dado")
    
    # Campo calculado: período formatado
    @property
    def periodo_formatado(self) -> str:
        """Retorna período formatado: 2024-Q3"""
        return f"{self.ano}-Q{self.trimestre}"
    
    class Config:
        from_attributes = True


# =============================================================
# SCHEMAS DE ESTATÍSTICAS
# =============================================================
class TopOperadoraResponse(BaseModel):
    """
    Schema para operadora no ranking top 5.
    """
    razao_social: str
    total: float


class EstatisticasResponse(BaseModel):
    """
    Schema de resposta para estatísticas agregadas.
    
    Usado no endpoint GET /api/estatisticas.
    
    CACHE:
    Este endpoint é cacheado por 15 minutos (ver router).
    Os dados de despesas são atualizados trimestralmente,
    então cache é seguro e melhora muito a performance.
    """
    total_despesas: float = Field(..., description="Soma de todas as despesas")
    media_despesas: float = Field(..., description="Média de despesas por registro")
    quantidade_registros: int = Field(..., description="Total de registros de despesa")
    top_5_operadoras: List[TopOperadoraResponse] = Field(
        ..., description="5 operadoras com maiores despesas"
    )


class DistribuicaoUFResponse(BaseModel):
    """
    Schema para distribuição de despesas por UF.
    
    Usado no gráfico do frontend.
    """
    uf: str = Field(..., description="Sigla do estado")
    total: float = Field(..., description="Total de despesas no estado")
    percentual: float = Field(..., description="Percentual do total geral")


class OperadoraAcimaMediaResponse(BaseModel):
    """
    Schema para operadoras que ficaram acima da média em 2+ trimestres.
    
    Query 3 dos requisitos: Identificar operadoras consistentemente
    acima da média de despesas do mercado.
    """
    cnpj: str = Field(..., description="CNPJ da operadora")
    razao_social: str = Field(..., description="Nome da operadora")
    total_trimestres: int = Field(..., description="Total de trimestres com dados")
    trimestres_acima_media: int = Field(..., description="Trimestres acima da média geral")
    media_operadora: float = Field(..., description="Média de despesas da operadora")
    total_despesas: float = Field(..., description="Total de despesas da operadora")


# =============================================================
# SCHEMAS DE PAGINAÇÃO
# =============================================================
# DECISÃO: Usar schemas específicos de paginação.
# JUSTIFICATIVA:
# - Compatibilidade com Python 3.9 e Pydantic v2.
# - Evita problemas de geração do OpenAPI schema.
# - Frontend pode usar o mesmo componente de paginação.
# =============================================================

class PaginatedOperadoraResponse(BaseModel):
    """
    Schema para respostas paginadas de operadoras.
    """
    data: List[OperadoraResponse] = Field(..., description="Items da página atual")
    total: int = Field(..., description="Total de items")
    page: int = Field(..., ge=1, description="Página atual")
    limit: int = Field(..., ge=1, le=100, description="Items por página")


class PaginatedDespesaResponse(BaseModel):
    """
    Schema para respostas paginadas de despesas.
    """
    data: List[DespesaResponse] = Field(..., description="Items da página atual")
    total: int = Field(..., description="Total de items")
    page: int = Field(..., ge=1, description="Página atual")
    limit: int = Field(..., ge=1, le=100, description="Items por página")


# =============================================================
# SCHEMAS DE ERRO
# =============================================================
class ErrorResponse(BaseModel):
    """
    Schema padrão para respostas de erro.
    
    DECISÃO: Padronizar respostas de erro.
    JUSTIFICATIVA:
    - Frontend pode tratar erros de forma consistente.
    - Facilita debugging (detail tem info adicional).
    - Segue boas práticas de API design.
    """
    error: str = Field(..., description="Mensagem de erro para o usuário")
    detail: Optional[str] = Field(None, description="Detalhes técnicos (para debugging)")
    code: Optional[str] = Field(None, description="Código de erro (para i18n)")


class HealthCheckResponse(BaseModel):
    """
    Schema para endpoint de health check.
    
    Usado por load balancers e monitoring.
    """
    status: str = Field(default="healthy")
    version: str
    timestamp: datetime
