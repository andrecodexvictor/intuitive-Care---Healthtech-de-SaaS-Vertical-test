# =============================================================
# interfaces.py - Interfaces de Repositório (Contratos Abstratos)
# =============================================================
# ARQUITETURA: Clean Architecture - Inversão de Dependência
#
# CONCEITO:
# Interfaces (Abstract Base Classes) definem contratos que os
# repositórios devem implementar. Isso permite:
# 1. Testar Use Cases com mock repositories.
# 2. Trocar implementação (MySQL -> PostgreSQL) sem mudar Use Cases.
# 3. Documentar claramente o que cada repositório deve fazer.
#
# PADRÃO: Repository Pattern
# - Repositório encapsula acesso a dados.
# - Use Case recebe repositório via injeção de dependência.
# - Use Case não sabe se é MySQL, PostgreSQL, ou arquivo JSON.
# =============================================================
from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities import Operadora, DespesaFinanceira, DespesaAgregada


class IOperadoraRepository(ABC):
    """
    Interface para repositório de Operadoras.
    
    MÉTODOS OBRIGATÓRIOS:
    Qualquer implementação (MySQL, PostgreSQL, Memory) deve ter estes métodos.
    """
    
    @abstractmethod
    async def get_by_cnpj(self, cnpj: str) -> Optional[Operadora]:
        """
        Busca operadora por CNPJ.
        
        Args:
            cnpj: CNPJ da operadora (14 dígitos, sem formatação)
        
        Returns:
            Operadora se encontrada, None caso contrário.
        """
        pass
    
    @abstractmethod
    async def list_all(
        self,
        page: int = 1,
        limit: int = 20,
        razao_social_filter: Optional[str] = None,
        cnpj_filter: Optional[str] = None
    ) -> tuple[List[Operadora], int]:
        """
        Lista operadoras com paginação e filtros opcionais.
        
        PAGINAÇÃO:
        DECISÃO: Offset-based (page/limit) ao invés de cursor-based.
        JUSTIFICATIVA:
        - Dados são relativamente estáticos (atualizados trimestralmente).
        - Simplicidade de implementação.
        - Facilidade no frontend (saber total de páginas).
        
        TRADE-OFF:
        - Cursor-based seria melhor para dados muito dinâmicos.
        - Offset fica lento com milhões de registros (OFFSET 1000000).
        - Para ~5000 operadoras, offset funciona perfeitamente.
        
        Args:
            page: Número da página (começa em 1)
            limit: Quantidade por página
            razao_social_filter: Filtro por razão social (LIKE %filtro%)
            cnpj_filter: Filtro por CNPJ (LIKE %filtro%)
        
        Returns:
            Tupla (lista de operadoras, total de registros)
        """
        pass
    
    @abstractmethod
    async def save(self, operadora: Operadora) -> Operadora:
        """
        Salva ou atualiza uma operadora.
        
        Se CNPJ já existe, atualiza. Caso contrário, insere.
        """
        pass
    
    @abstractmethod
    async def save_batch(self, operadoras: List[Operadora]) -> int:
        """
        Salva múltiplas operadoras em batch.
        
        PERFORMANCE:
        Inserção em batch é muito mais rápida que individual.
        5000 operadoras: batch ~2s vs individual ~30s
        
        Returns:
            Quantidade de registros salvos.
        """
        pass


class IDespesaRepository(ABC):
    """
    Interface para repositório de Despesas Financeiras.
    """
    
    @abstractmethod
    async def get_by_operadora(
        self,
        cnpj: str,
        ano: Optional[int] = None,
        trimestre: Optional[int] = None
    ) -> List[DespesaFinanceira]:
        """
        Busca despesas de uma operadora, opcionalmente filtradas por período.
        """
        pass
    
    @abstractmethod
    async def save_batch(self, despesas: List[DespesaFinanceira]) -> int:
        """
        Salva múltiplas despesas em batch.
        """
        pass
    
    @abstractmethod
    async def get_estatisticas_gerais(self) -> dict:
        """
        Retorna estatísticas agregadas de todas as despesas.
        
        CACHE:
        DECISÃO: Implementar cache na camada de infraestrutura.
        Este método pode ser custoso (agregação de milhares de registros).
        A infraestrutura decide se cacheia (Redis, lru_cache, etc.).
        
        Returns:
            Dict com: total_despesas, media, top_5_operadoras
        """
        pass


class IDespesaAgregadaRepository(ABC):
    """
    Interface para repositório de Despesas Agregadas.
    """
    
    @abstractmethod
    async def get_all_ordered(self) -> List[DespesaAgregada]:
        """
        Retorna todas as despesas agregadas ordenadas por valor total (desc).
        """
        pass
    
    @abstractmethod
    async def save_batch(self, agregadas: List[DespesaAgregada]) -> int:
        """
        Salva despesas agregadas calculadas.
        """
        pass
