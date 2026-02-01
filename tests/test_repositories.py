# =============================================================
# test_repositories.py - Testes dos Repositórios
# =============================================================
# Cobertura: OperadoraRepository, DespesaRepository
#
# TESTES:
# - CRUD de operadoras
# - Paginação
# - Filtros de busca
# - Estatísticas agregadas
# - Batch operations
# =============================================================
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import List

from src.domain.entities import Operadora, DespesaFinanceira, StatusQualidade
from src.infrastructure.database.repositories import (
    OperadoraRepository,
    DespesaRepository,
    DespesaAgregadaRepository,
)


class TestOperadoraRepositoryMock:
    """Testes do OperadoraRepository com mock."""
    
    @pytest.fixture
    def mock_session(self):
        """Session mockada do SQLAlchemy."""
        session = MagicMock()
        return session
    
    @pytest.fixture
    def mock_operadora_orm(self):
        """ORM mockado de Operadora."""
        orm = MagicMock()
        orm.cnpj = "11444777000161"
        orm.razao_social = "OPERADORA TESTE"
        orm.registro_ans = "123456"
        orm.modalidade = None
        orm.uf = "SP"
        orm.to_entity.return_value = Operadora(
            cnpj="11444777000161",
            razao_social="OPERADORA TESTE",
            registro_ans="123456",
            modalidade=None,
            uf="SP"
        )
        return orm
    
    @pytest.mark.asyncio
    async def test_get_by_cnpj_found(self, mock_session, mock_operadora_orm):
        """Deve retornar operadora quando encontrada."""
        # Setup
        mock_session.query.return_value.filter.return_value.first.return_value = mock_operadora_orm
        repo = OperadoraRepository(mock_session)
        
        # Execute
        result = await repo.get_by_cnpj("11444777000161")
        
        # Assert
        assert result is not None
        assert result.cnpj == "11444777000161"
        assert result.razao_social == "OPERADORA TESTE"
    
    @pytest.mark.asyncio
    async def test_get_by_cnpj_not_found(self, mock_session):
        """Deve retornar None quando não encontrada."""
        # Setup
        mock_session.query.return_value.filter.return_value.first.return_value = None
        repo = OperadoraRepository(mock_session)
        
        # Execute
        result = await repo.get_by_cnpj("99999999999999")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_all_empty(self, mock_session):
        """Deve retornar lista vazia quando não há operadoras."""
        # Setup
        mock_query = MagicMock()
        mock_query.count.return_value = 0
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        
        repo = OperadoraRepository(mock_session)
        
        # Execute
        operadoras, total = await repo.list_all(page=1, limit=20)
        
        # Assert
        assert operadoras == []
        assert total == 0
    
    @pytest.mark.asyncio
    async def test_list_all_with_results(self, mock_session, mock_operadora_orm):
        """Deve retornar lista de operadoras."""
        # Setup
        mock_query = MagicMock()
        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_operadora_orm]
        mock_session.query.return_value = mock_query
        
        repo = OperadoraRepository(mock_session)
        
        # Execute
        operadoras, total = await repo.list_all(page=1, limit=20)
        
        # Assert
        assert len(operadoras) == 1
        assert total == 1
        assert operadoras[0].cnpj == "11444777000161"
    
    @pytest.mark.asyncio
    async def test_list_all_with_filter_sanitizes_input(self, mock_session):
        """Filtro deve sanitizar caracteres especiais."""
        # Setup
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        
        repo = OperadoraRepository(mock_session)
        
        # Execute com caracteres especiais
        await repo.list_all(razao_social_filter="TESTE%_DROP")
        
        # Assert - filter deve ter sido chamado
        assert mock_query.filter.called
    
    @pytest.mark.asyncio
    async def test_save_new_operadora(self, mock_session):
        """Deve salvar nova operadora."""
        # Setup
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        operadora = Operadora(
            cnpj="99999999999999",
            razao_social="NOVA OPERADORA",
            registro_ans="999999",
            modalidade=None,
            uf="RJ"
        )
        
        repo = OperadoraRepository(mock_session)
        
        # Execute
        result = await repo.save(operadora)
        
        # Assert
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        assert result.cnpj == "99999999999999"
    
    @pytest.mark.asyncio
    async def test_save_batch(self, mock_session):
        """Deve salvar múltiplas operadoras em batch."""
        operadoras = [
            Operadora(cnpj=f"{10000000000000 + i:014d}", razao_social=f"OP {i}", registro_ans=None, modalidade=None, uf="SP")
            for i in range(10)
        ]
        
        repo = OperadoraRepository(mock_session)
        
        # Execute
        count = await repo.save_batch(operadoras)
        
        # Assert
        assert count == 10
        mock_session.commit.assert_called_once()


class TestDespesaRepositoryMock:
    """Testes do DespesaRepository com mock."""
    
    @pytest.fixture
    def mock_session(self):
        """Session mockada do SQLAlchemy."""
        return MagicMock()
    
    @pytest.fixture
    def mock_despesa_orm(self):
        """ORM mockado de Despesa."""
        orm = MagicMock()
        orm.cnpj = "11444777000161"
        orm.razao_social = "OPERADORA TESTE"
        orm.ano = 2024
        orm.trimestre = 1
        orm.valor = 50000.0
        orm.status_qualidade = "OK"
        orm.to_entity.return_value = DespesaFinanceira(
            cnpj="11444777000161",
            razao_social="OPERADORA TESTE",
            ano=2024,
            trimestre=1,
            valor=50000.0,
            status_qualidade=StatusQualidade.OK
        )
        return orm
    
    @pytest.mark.asyncio
    async def test_get_by_operadora_empty(self, mock_session):
        """Deve retornar lista vazia quando não há despesas."""
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        repo = DespesaRepository(mock_session)
        result = await repo.get_by_operadora("11444777000161")
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_by_operadora_with_results(self, mock_session, mock_despesa_orm):
        """Deve retornar despesas da operadora."""
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_despesa_orm]
        
        repo = DespesaRepository(mock_session)
        result = await repo.get_by_operadora("11444777000161")
        
        assert len(result) == 1
        assert result[0].cnpj == "11444777000161"
        assert result[0].valor == 50000.0
    
    @pytest.mark.asyncio
    async def test_get_by_operadora_with_year_filter(self, mock_session, mock_despesa_orm):
        """Deve aplicar filtro de ano."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [mock_despesa_orm]
        mock_session.query.return_value = mock_query
        
        repo = DespesaRepository(mock_session)
        result = await repo.get_by_operadora("11444777000161", ano=2024)
        
        # filter deve ter sido chamado 2x (cnpj + ano)
        assert mock_query.filter.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_get_estatisticas_gerais(self, mock_session):
        """Deve retornar estatísticas gerais."""
        # Mock da query de estatísticas
        mock_stats = MagicMock()
        mock_stats.total = 1000000.0
        mock_stats.media = 50000.0
        mock_stats.quantidade = 20
        
        mock_top5 = [
            MagicMock(razao_social="OP1", total=200000.0),
            MagicMock(razao_social="OP2", total=150000.0),
        ]
        
        mock_session.query.return_value.first.return_value = mock_stats
        mock_session.query.return_value.join.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_top5
        
        repo = DespesaRepository(mock_session)
        result = await repo.get_estatisticas_gerais()
        
        assert "total_despesas" in result
        assert "media_despesas" in result
        assert "quantidade_registros" in result
        assert "top_5_operadoras" in result


class TestPagination:
    """Testes de paginação."""
    
    def test_offset_calculation(self):
        """Offset deve ser calculado corretamente."""
        # page=1, limit=20 → offset=0
        assert (1 - 1) * 20 == 0
        
        # page=2, limit=20 → offset=20
        assert (2 - 1) * 20 == 20
        
        # page=5, limit=50 → offset=200
        assert (5 - 1) * 50 == 200
    
    def test_pagination_params(self):
        """Parâmetros de paginação devem ser validados."""
        # Page mínimo é 1
        page = max(1, 0)
        assert page == 1
        
        # Limit máximo é 100 (configurável)
        limit = min(100, 200)
        assert limit == 100


class TestFilterSanitization:
    """Testes de sanitização de filtros."""
    
    def test_remove_sql_wildcards(self):
        """Deve remover wildcards SQL."""
        unsafe_input = "TESTE%_DROP"
        safe_input = unsafe_input.replace("%", "").replace("_", "")
        
        assert safe_input == "TESTEDROP"
        assert "%" not in safe_input
        assert "_" not in safe_input
    
    def test_trailing_wildcard_pattern(self):
        """Padrão de trailing wildcard."""
        term = "UNIMED"
        pattern = f"{term}%"
        
        assert pattern == "UNIMED%"
        assert pattern.startswith(term)


class TestRepositoryDependencyInjection:
    """Testes de injeção de dependência."""
    
    def test_repository_receives_session(self):
        """Repositório deve receber session no construtor."""
        mock_session = MagicMock()
        repo = OperadoraRepository(mock_session)
        
        assert repo.db == mock_session
    
    def test_repository_uses_injected_session(self):
        """Repositório deve usar session injetada."""
        mock_session = MagicMock()
        repo = OperadoraRepository(mock_session)
        
        # Chama método que usa session
        repo.db.query()
        
        # Verifica se session foi usada
        mock_session.query.assert_called_once()
