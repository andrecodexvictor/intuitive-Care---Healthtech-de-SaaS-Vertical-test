# =============================================================
# repositories.py - Implementação dos Repositórios (MySQL)
# =============================================================
# ARQUITETURA: Clean Architecture - Infraestrutura
#
# Este arquivo IMPLEMENTA as interfaces definidas em application/interfaces.py.
# A implementação usa SQLAlchemy para acessar MySQL.
#
# PADRÃO: Repository Pattern
# - Encapsula toda lógica de acesso a dados.
# - Use Cases não sabem que é MySQL (só conhecem a interface).
# - Facilita testes com mock repositories.
# =============================================================
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from src.application.interfaces import (
    IOperadoraRepository,
    IDespesaRepository,
    IDespesaAgregadaRepository,
)
from src.domain.entities import Operadora, DespesaFinanceira, DespesaAgregada
from src.infrastructure.database.models import OperadoraORM, DespesaORM, DespesaAgregadaORM


class OperadoraRepository(IOperadoraRepository):
    """
    Implementação MySQL do repositório de Operadoras.
    
    INJEÇÃO DE DEPENDÊNCIA:
    A session do banco é injetada no construtor.
    Isso permite usar a mesma session em toda a requisição
    e também facilita testes (injetar mock session).
    """
    
    def __init__(self, db: Session):
        """
        Inicializa o repositório com uma session do SQLAlchemy.
        
        Args:
            db: Session ativa do SQLAlchemy (injetada via FastAPI Depends)
        """
        self.db = db
    
    async def get_by_cnpj(self, cnpj: str) -> Optional[Operadora]:
        """
        Busca operadora por CNPJ.
        
        QUERY GERADA:
        SELECT * FROM operadoras WHERE cnpj = :cnpj LIMIT 1
        
        PERFORMANCE:
        - CNPJ é Primary Key = índice automático.
        - Busca é O(log n) = muito rápido.
        """
        orm_obj = self.db.query(OperadoraORM).filter(
            OperadoraORM.cnpj == cnpj
        ).first()
        
        if orm_obj is None:
            return None
        
        return orm_obj.to_entity()
    
    async def list_all(
        self,
        page: int = 1,
        limit: int = 20,
        razao_social_filter: Optional[str] = None,
        cnpj_filter: Optional[str] = None
    ) -> tuple[List[Operadora], int]:
        """
        Lista operadoras com paginação offset-based.
        
        IMPLEMENTAÇÃO DA PAGINAÇÃO:
        - Offset = (page - 1) * limit
        - Exemplo: page=2, limit=20 → OFFSET 20 LIMIT 20
        
        QUERY GERADA (com filtros):
        SELECT * FROM operadoras
        WHERE razao_social LIKE '%filtro%'
        ORDER BY razao_social
        LIMIT 20 OFFSET 40
        
        PERFORMANCE:
        - OFFSET grande é lento (MySQL precisa pular N registros).
        - Para ~5000 operadoras, é aceitável.
        - Se fosse 1 milhão, usaríamos cursor-based.
        """
        query = self.db.query(OperadoraORM)
        
        # Aplica filtros
        if razao_social_filter:
            query = query.filter(
                OperadoraORM.razao_social.ilike(f"%{razao_social_filter}%")
            )
        
        if cnpj_filter:
            query = query.filter(
                OperadoraORM.cnpj.like(f"%{cnpj_filter}%")
            )
        
        # Conta total (para paginação no frontend)
        total = query.count()
        
        # Aplica ordenação e paginação
        offset = (page - 1) * limit
        results = query.order_by(OperadoraORM.razao_social).offset(offset).limit(limit).all()
        
        # Converte ORM -> Entidades
        entities = [r.to_entity() for r in results]
        
        return entities, total
    
    async def save(self, operadora: Operadora) -> Operadora:
        """
        Salva ou atualiza operadora (upsert).
        
        ESTRATÉGIA:
        - Tenta buscar por CNPJ.
        - Se existe, atualiza campos.
        - Se não existe, insere novo.
        """
        existing = self.db.query(OperadoraORM).filter(
            OperadoraORM.cnpj == operadora.cnpj
        ).first()
        
        if existing:
            # Atualiza
            existing.razao_social = operadora.razao_social
            existing.registro_ans = operadora.registro_ans
            existing.modalidade = operadora.modalidade.value if operadora.modalidade else None
            existing.uf = operadora.uf
        else:
            # Insere
            new_orm = OperadoraORM.from_entity(operadora)
            self.db.add(new_orm)
        
        self.db.commit()
        return operadora
    
    async def save_batch(self, operadoras: List[Operadora]) -> int:
        """
        Salva múltiplas operadoras em batch.
        
        PERFORMANCE:
        - Usa bulk_save_objects para inserção rápida.
        - Evita N commits (1 commit só no final).
        - 5000 operadoras: ~2s ao invés de ~30s.
        
        LIMITAÇÃO:
        - bulk_save_objects não dispara eventos ORM.
        - Se precisasse de hooks, usaríamos add_all().
        """
        orm_objects = [OperadoraORM.from_entity(o) for o in operadoras]
        
        # Usa merge ao invés de add para fazer upsert
        for orm_obj in orm_objects:
            self.db.merge(orm_obj)
        
        self.db.commit()
        return len(operadoras)


class DespesaRepository(IDespesaRepository):
    """
    Implementação MySQL do repositório de Despesas Financeiras.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_by_operadora(
        self,
        cnpj: str,
        ano: Optional[int] = None,
        trimestre: Optional[int] = None
    ) -> List[DespesaFinanceira]:
        """
        Busca despesas de uma operadora.
        
        ORDENAÇÃO: Por período (ano, trimestre) descendente.
        Assim, os dados mais recentes aparecem primeiro.
        """
        query = self.db.query(DespesaORM).filter(DespesaORM.cnpj == cnpj)
        
        if ano:
            query = query.filter(DespesaORM.ano == ano)
        
        if trimestre:
            query = query.filter(DespesaORM.trimestre == trimestre)
        
        results = query.order_by(
            desc(DespesaORM.ano),
            desc(DespesaORM.trimestre)
        ).all()
        
        return [r.to_entity() for r in results]
    
    async def save_batch(self, despesas: List[DespesaFinanceira]) -> int:
        """
        Salva múltiplas despesas em batch.
        """
        orm_objects = [DespesaORM.from_entity(d) for d in despesas]
        self.db.bulk_save_objects(orm_objects)
        self.db.commit()
        return len(despesas)
    
    async def get_estatisticas_gerais(self) -> dict:
        """
        Calcula estatísticas gerais de todas as despesas.
        
        QUERY AGREGADA:
        SELECT 
            SUM(valor) as total,
            AVG(valor) as media,
            COUNT(*) as quantidade
        FROM despesas
        
        CACHE:
        DECISÃO: Usar @lru_cache no Use Case.
        JUSTIFICATIVA:
        - Esta query é custosa (agrega todos os registros).
        - Dados mudam apenas trimestralmente.
        - Cache de 15 minutos é suficiente.
        """
        # Estatísticas gerais
        stats = self.db.query(
            func.sum(DespesaORM.valor).label("total"),
            func.avg(DespesaORM.valor).label("media"),
            func.count(DespesaORM.id).label("quantidade"),
        ).first()
        
        # Top 5 operadoras por despesa total
        top_5 = self.db.query(
            DespesaORM.razao_social,
            func.sum(DespesaORM.valor).label("total")
        ).group_by(
            DespesaORM.razao_social
        ).order_by(
            desc(func.sum(DespesaORM.valor))
        ).limit(5).all()
        
        return {
            "total_despesas": float(stats.total or 0),
            "media_despesas": float(stats.media or 0),
            "quantidade_registros": int(stats.quantidade or 0),
            "top_5_operadoras": [
                {"razao_social": r.razao_social, "total": float(r.total)}
                for r in top_5
            ]
        }


class DespesaAgregadaRepository(IDespesaAgregadaRepository):
    """
    Implementação MySQL do repositório de Despesas Agregadas.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_all_ordered(self) -> List[DespesaAgregada]:
        """
        Retorna todas as despesas agregadas ordenadas por total (desc).
        """
        results = self.db.query(DespesaAgregadaORM).order_by(
            desc(DespesaAgregadaORM.total)
        ).all()
        
        return [
            DespesaAgregada(
                razao_social=r.razao_social,
                uf=r.uf,
                total=r.total,
                media=r.media,
                desvio_padrao=r.desvio_padrao,
                quantidade_registros=r.quantidade_registros,
            )
            for r in results
        ]
    
    async def save_batch(self, agregadas: List[DespesaAgregada]) -> int:
        """
        Salva despesas agregadas (limpa tabela antes).
        
        ESTRATÉGIA: Truncate + Insert
        Como agregações são recalculadas do zero,
        é mais simples limpar e reinserir.
        """
        # Limpa tabela existente
        self.db.query(DespesaAgregadaORM).delete()
        
        # Insere novos dados
        for a in agregadas:
            orm_obj = DespesaAgregadaORM(
                razao_social=a.razao_social,
                uf=a.uf,
                total=a.total,
                media=a.media,
                desvio_padrao=a.desvio_padrao,
                quantidade_registros=a.quantidade_registros,
            )
            self.db.add(orm_obj)
        
        self.db.commit()
        return len(agregadas)
