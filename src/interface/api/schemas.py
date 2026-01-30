# =============================================================
# schemas.py - Schemas de Request/Response da API
# =============================================================
# ARQUITETURA: Clean Architecture - Interface Layer
#
# DIFERENÇA ENTRE SCHEMAS E ENTITIES:
# - Entities (domain/entities.py): Modelo de negócio interno.
# - Schemas (este arquivo): Contrato da API (o que o cliente vê).
#
# POR QUE SEPARAR?
# 1. API pode ter campos diferentes da entidade interna.
#    Ex: Entidade tem "status_qualidade", API pode traduzir para PT.
# 2. Versionamento: API v1 pode ter schema diferente de API v2.
# 3. Segurança: Não expor campos internos (ex: hashes, flags debug).
#
# CONVENÇÃO:
# - *Request: Dados recebidos do cliente.
# - *Response: Dados enviados ao cliente.
# - *InDB: Representação completa (inclui IDs gerados).
# =============================================================
from pydantic import BaseModel, Field
from typing import List, Optional, Generic, TypeVar
from datetime import datetime


# =============================================================
# SCHEMAS DE OPERADORA
# =============================================================
class OperadoraResponse(BaseModel):
    """
    Schema de resposta para dados de uma operadora.
    
    DECISÃO: Expor todos os campos da entidade.
    JUSTIFICATIVA: 
    - Não há dados sensíveis em operadoras.
    - Frontend precisa de todas as informações.
    """
    cnpj: str = Field(..., description="CNPJ da operadora (14 dígitos)")
    razao_social: str = Field(..., description="Nome oficial da operadora")
    registro_ans: Optional[str] = Field(None, description="Registro na ANS (6 dígitos)")
    modalidade: Optional[str] = Field(None, description="Modalidade de operação")
    uf: Optional[str] = Field(None, description="UF da sede")
    
    # DECISÃO: Formatar CNPJ na resposta.
    # JUSTIFICATIVA: Facilita leitura no frontend.
    @property
    def cnpj_formatado(self) -> str:
        """Retorna CNPJ formatado: XX.XXX.XXX/XXXX-XX"""
        v = self.cnpj
        return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
    
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


# =============================================================
# SCHEMAS DE PAGINAÇÃO
# =============================================================
# DECISÃO: Usar schema genérico de paginação.
# JUSTIFICATIVA:
# - Evita repetição (DRY).
# - Garantia de resposta consistente em todos os endpoints.
# - Frontend pode usar o mesmo componente de paginação.
# =============================================================
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Schema genérico para respostas paginadas.
    
    CAMPOS:
    - data: Lista de items da página atual.
    - total: Total de items (todas as páginas).
    - page: Página atual (começa em 1).
    - limit: Items por página.
    - pages: Total de páginas (calculado).
    
    DECISÃO: Incluir metadados de paginação.
    JUSTIFICATIVA:
    - Frontend precisa saber total para exibir paginação.
    - Padrão comum em APIs REST.
    - Facilita implementação de "Load More" ou "Infinite Scroll".
    """
    data: List[T] = Field(..., description="Items da página atual")
    total: int = Field(..., description="Total de items")
    page: int = Field(..., ge=1, description="Página atual")
    limit: int = Field(..., ge=1, le=100, description="Items por página")
    
    @property
    def pages(self) -> int:
        """Calcula total de páginas."""
        if self.limit == 0:
            return 0
        return (self.total + self.limit - 1) // self.limit
    
    @property
    def has_next(self) -> bool:
        """Indica se há próxima página."""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """Indica se há página anterior."""
        return self.page > 1


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
