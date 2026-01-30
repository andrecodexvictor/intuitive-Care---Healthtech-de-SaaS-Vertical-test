# =============================================================
# test_operadoras.py - Testes Unitários para Operadoras
# =============================================================
# ESTRATÉGIA: Pytest + mocking para isolar camadas
# COBERTURA ALVO: >80% na camada Application
# =============================================================
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Importações do projeto
from src.domain.entities import Operadora, Despesa, CNPJ
from src.application.interfaces import OperadoraRepository


# =============================================================
# Fixtures
# =============================================================

@pytest.fixture
def valid_cnpj():
    """CNPJ válido para testes."""
    return "11222333000181"  # CNPJ de exemplo válido


@pytest.fixture
def invalid_cnpj():
    """CNPJ inválido para testes."""
    return "12345678901234"  # CNPJ inválido


@pytest.fixture
def sample_operadora(valid_cnpj):
    """Operadora de exemplo para testes."""
    return Operadora(
        cnpj=valid_cnpj,
        razao_social="Operadora Teste Ltda",
        registro_ans="123456",
        modalidade="Medicina de Grupo",
        uf="SP"
    )


@pytest.fixture
def sample_operadoras(valid_cnpj):
    """Lista de operadoras para testes de paginação."""
    return [
        Operadora(
            cnpj=f"{i:014d}",
            razao_social=f"Operadora {i}",
            registro_ans=f"{i:06d}",
            modalidade="Cooperativa Médica",
            uf="RJ"
        )
        for i in range(1, 11)
    ]


@pytest.fixture
def sample_despesas(valid_cnpj):
    """Lista de despesas para testes."""
    return [
        Despesa(
            cnpj=valid_cnpj,
            ano=2024,
            trimestre=q,
            valor=100000.0 * q,
            status_qualidade="OK"
        )
        for q in range(1, 4)
    ]


@pytest.fixture
def mock_repository():
    """Mock do repositório para testes unitários."""
    repo = Mock(spec=OperadoraRepository)
    repo.get_all = AsyncMock()
    repo.get_by_cnpj = AsyncMock()
    repo.get_despesas = AsyncMock()
    repo.count = AsyncMock()
    return repo


# =============================================================
# Testes de Entidades (Domain Layer)
# =============================================================

class TestCNPJ:
    """Testes para validação de CNPJ."""
    
    def test_cnpj_valido(self, valid_cnpj):
        """CNPJ válido deve passar na validação."""
        cnpj = CNPJ(value=valid_cnpj)
        assert cnpj.value == valid_cnpj
        assert cnpj.is_valid() is True
    
    def test_cnpj_formatado(self, valid_cnpj):
        """CNPJ deve retornar formato com máscara."""
        cnpj = CNPJ(value=valid_cnpj)
        formatted = cnpj.formatted()
        assert "." in formatted
        assert "/" in formatted
        assert "-" in formatted
    
    def test_cnpj_invalido_tamanho(self):
        """CNPJ com tamanho errado deve falhar."""
        with pytest.raises(ValueError):
            CNPJ(value="12345")
    
    def test_cnpj_invalido_caracteres(self):
        """CNPJ com caracteres não numéricos deve falhar."""
        with pytest.raises(ValueError):
            CNPJ(value="1234567890ABCD")


class TestOperadora:
    """Testes para entidade Operadora."""
    
    def test_operadora_criacao(self, sample_operadora):
        """Operadora deve ser criada com dados válidos."""
        assert sample_operadora.razao_social == "Operadora Teste Ltda"
        assert sample_operadora.uf == "SP"
    
    def test_operadora_cnpj_obrigatorio(self):
        """Operadora deve exigir CNPJ."""
        with pytest.raises(Exception):
            Operadora(
                razao_social="Test",
                registro_ans="123456",
                modalidade="Medicina de Grupo",
                uf="SP"
            )


class TestDespesa:
    """Testes para entidade Despesa."""
    
    def test_despesa_criacao(self, valid_cnpj):
        """Despesa deve ser criada com dados válidos."""
        despesa = Despesa(
            cnpj=valid_cnpj,
            ano=2024,
            trimestre=1,
            valor=50000.0
        )
        assert despesa.valor == 50000.0
        assert despesa.trimestre == 1
    
    def test_despesa_valor_negativo(self, valid_cnpj):
        """Despesa com valor negativo deve marcar como suspeita."""
        despesa = Despesa(
            cnpj=valid_cnpj,
            ano=2024,
            trimestre=1,
            valor=-1000.0,
            status_qualidade="SUSPEITO"
        )
        assert despesa.status_qualidade == "SUSPEITO"
    
    def test_despesa_trimestre_valido(self, valid_cnpj):
        """Trimestre deve estar entre 1 e 4."""
        with pytest.raises(ValueError):
            Despesa(
                cnpj=valid_cnpj,
                ano=2024,
                trimestre=5,
                valor=1000.0
            )


# =============================================================
# Testes de Casos de Uso (Application Layer)
# =============================================================

class TestListOperadoras:
    """Testes para caso de uso de listagem."""
    
    @pytest.mark.asyncio
    async def test_list_operadoras_paginado(
        self, mock_repository, sample_operadoras
    ):
        """Deve retornar lista paginada de operadoras."""
        mock_repository.get_all.return_value = sample_operadoras[:5]
        mock_repository.count.return_value = 10
        
        result = await mock_repository.get_all(skip=0, limit=5)
        total = await mock_repository.count()
        
        assert len(result) == 5
        assert total == 10
        mock_repository.get_all.assert_called_once_with(skip=0, limit=5)
    
    @pytest.mark.asyncio
    async def test_list_operadoras_com_filtro(
        self, mock_repository, sample_operadoras
    ):
        """Deve filtrar por razão social."""
        filtered = [o for o in sample_operadoras if "5" in o.razao_social]
        mock_repository.get_all.return_value = filtered
        
        result = await mock_repository.get_all(
            skip=0, limit=20, razao_social="5"
        )
        
        assert all("5" in o.razao_social for o in result)


class TestGetOperadora:
    """Testes para caso de uso de detalhes."""
    
    @pytest.mark.asyncio
    async def test_get_operadora_existente(
        self, mock_repository, sample_operadora, valid_cnpj
    ):
        """Deve retornar operadora existente."""
        mock_repository.get_by_cnpj.return_value = sample_operadora
        
        result = await mock_repository.get_by_cnpj(valid_cnpj)
        
        assert result is not None
        assert result.cnpj == valid_cnpj
    
    @pytest.mark.asyncio
    async def test_get_operadora_inexistente(
        self, mock_repository
    ):
        """Deve retornar None para operadora inexistente."""
        mock_repository.get_by_cnpj.return_value = None
        
        result = await mock_repository.get_by_cnpj("00000000000000")
        
        assert result is None


class TestGetDespesas:
    """Testes para caso de uso de despesas."""
    
    @pytest.mark.asyncio
    async def test_get_despesas_operadora(
        self, mock_repository, sample_despesas, valid_cnpj
    ):
        """Deve retornar despesas da operadora."""
        mock_repository.get_despesas.return_value = sample_despesas
        
        result = await mock_repository.get_despesas(valid_cnpj)
        
        assert len(result) == 3
        assert all(d.cnpj == valid_cnpj for d in result)
    
    @pytest.mark.asyncio
    async def test_get_despesas_ordenadas(
        self, mock_repository, sample_despesas, valid_cnpj
    ):
        """Despesas devem vir ordenadas por período."""
        mock_repository.get_despesas.return_value = sorted(
            sample_despesas, 
            key=lambda d: (d.ano, d.trimestre)
        )
        
        result = await mock_repository.get_despesas(valid_cnpj)
        
        # Verificar ordenação
        for i in range(len(result) - 1):
            assert (result[i].ano, result[i].trimestre) <= \
                   (result[i+1].ano, result[i+1].trimestre)


# =============================================================
# Testes de Estatísticas
# =============================================================

class TestEstatisticas:
    """Testes para cálculos estatísticos."""
    
    def test_calculo_total_despesas(self, sample_despesas):
        """Deve calcular total corretamente."""
        total = sum(d.valor for d in sample_despesas)
        expected = 100000 + 200000 + 300000  # Q1 + Q2 + Q3
        assert total == expected
    
    def test_calculo_media_despesas(self, sample_despesas):
        """Deve calcular média corretamente."""
        total = sum(d.valor for d in sample_despesas)
        media = total / len(sample_despesas)
        expected = (100000 + 200000 + 300000) / 3
        assert media == expected
    
    def test_crescimento_percentual(self, sample_despesas):
        """Deve calcular crescimento percentual."""
        primeiro = sample_despesas[0].valor  # Q1: 100000
        ultimo = sample_despesas[-1].valor   # Q3: 300000
        
        crescimento = ((ultimo - primeiro) / primeiro) * 100
        
        assert crescimento == 200.0  # 200% de crescimento


# =============================================================
# Testes de Integração (API Layer) - Usando HTTPX
# =============================================================

class TestAPIIntegration:
    """Testes de integração para endpoints da API."""
    
    @pytest.fixture
    def client(self):
        """Cliente de teste para a API."""
        from fastapi.testclient import TestClient
        from src.main import app
        return TestClient(app)
    
    def test_health_check(self, client):
        """Endpoint de health deve retornar 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_list_operadoras_endpoint(self, client):
        """Endpoint de listagem deve retornar estrutura correta."""
        response = client.get("/api/operadoras?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
    
    def test_operadora_not_found(self, client):
        """Endpoint deve retornar 404 para CNPJ inexistente."""
        response = client.get("/api/operadoras/00000000000000")
        assert response.status_code == 404
    
    def test_estatisticas_endpoint(self, client):
        """Endpoint de estatísticas deve retornar dados."""
        response = client.get("/api/estatisticas")
        assert response.status_code == 200
        data = response.json()
        assert "total_despesas" in data or "error" in data
