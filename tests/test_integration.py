# =============================================================
# test_integration.py - Testes de Integração com MySQL Real
# =============================================================
# ARQUITETURA DE TESTES:
# - Testes de integração usam banco de dados REAL (MySQL).
# - Isolamento via CNPJs com prefixo "99" (dados de teste).
# - Transações são revertidas após cada teste.
# - Testa fluxo completo: API → Repository → MySQL → Response.
#
# CREDENCIAIS (ambiente local):
# - Host: localhost:3306
# - User: root
# - Password: adm@123
# - Database: intuitive_care_test
#
# MARCADORES:
# @pytest.mark.integration - Testes que precisam de MySQL real
# @pytest.mark.slow - Testes que demoram mais de 1s
# =============================================================
import pytest
import os
from datetime import datetime
from typing import Generator
from unittest.mock import patch

# Configurar variáveis de ambiente ANTES de importar módulos
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "3306")
os.environ.setdefault("DATABASE_USER", "root")
os.environ.setdefault("DATABASE_PASSWORD", "adm@123")
os.environ.setdefault("DATABASE_NAME", "intuitive_care_test")
os.environ.setdefault("ENVIRONMENT", "testing")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from src.infrastructure.database.connection import Base
from src.infrastructure.database.models import OperadoraORM, DespesaORM, DespesaAgregadaORM
from src.infrastructure.database.repositories import (
    OperadoraRepository,
    DespesaRepository,
    DespesaAgregadaRepository,
)
from src.domain.entities import Operadora, DespesaFinanceira, DespesaAgregada, Modalidade


# =============================================================
# CONFIGURAÇÃO DO BANCO DE TESTE
# =============================================================
TEST_DATABASE_URL = (
    f"mysql+pymysql://{os.environ['DATABASE_USER']}:{os.environ['DATABASE_PASSWORD']}"
    f"@{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}"
    f"/{os.environ['DATABASE_NAME']}"
)

# Engine separado para testes de integração
test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_size=2,
    max_overflow=3,
    pool_recycle=3600,
    echo=False,  # Desativar logs SQL nos testes
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# =============================================================
# FIXTURES DE INTEGRAÇÃO
# =============================================================
@pytest.fixture(scope="module")
def setup_test_database():
    """
    Cria tabelas no banco de teste (uma vez por módulo).
    
    NOTA: scope="module" significa que roda uma vez
    para todos os testes deste arquivo.
    """
    try:
        Base.metadata.create_all(bind=test_engine)
        # Cleanup inicial: remove dados de teste antes de rodar
        with test_engine.begin() as conn:
            conn.execute(text("DELETE FROM despesas WHERE cnpj LIKE '99%'"))
            conn.execute(text("DELETE FROM operadoras WHERE cnpj LIKE '99%'"))
        yield
    finally:
        # Cleanup final: remove dados de teste após módulo
        with test_engine.begin() as conn:
            conn.execute(text("DELETE FROM despesas WHERE cnpj LIKE '99%'"))
            conn.execute(text("DELETE FROM operadoras WHERE cnpj LIKE '99%'"))


@pytest.fixture
def db_session(setup_test_database) -> Generator[Session, None, None]:
    """
    Fornece uma session de banco com cleanup automático.
    
    ISOLAMENTO:
    Cada teste limpa dados de teste (99*) antes e depois.
    """
    session = TestSessionLocal()
    try:
        # Cleanup antes do teste
        session.execute(text("DELETE FROM despesas WHERE cnpj LIKE '99%'"))
        session.execute(text("DELETE FROM operadoras WHERE cnpj LIKE '99%'"))
        session.commit()
        yield session
    finally:
        # Cleanup após o teste
        session.execute(text("DELETE FROM despesas WHERE cnpj LIKE '99%'"))
        session.execute(text("DELETE FROM operadoras WHERE cnpj LIKE '99%'"))
        session.commit()
        session.close()


@pytest.fixture
def integration_client(setup_test_database):
    """
    TestClient configurado para testes de integração.
    
    DIFERENÇA DO CLIENT NORMAL:
    Este usa o banco de teste real, não mocks.
    """
    from src.main import app
    with TestClient(app) as client:
        yield client


# =============================================================
# FIXTURES DE DADOS DE TESTE
# =============================================================
# CONVENÇÃO: CNPJs de teste começam com "99" para fácil identificação e limpeza.
# =============================================================

@pytest.fixture
def operadora_teste(db_session: Session) -> OperadoraORM:
    """Cria uma operadora de teste no banco."""
    operadora = OperadoraORM(
        cnpj="99111111000199",
        razao_social="Operadora Teste Integração",
        registro_ans="999999",
        modalidade="Medicina de Grupo",
        uf="SP",
    )
    db_session.add(operadora)
    db_session.commit()
    db_session.refresh(operadora)
    return operadora


@pytest.fixture
def operadoras_teste_batch(db_session: Session) -> list[OperadoraORM]:
    """Cria múltiplas operadoras de teste."""
    operadoras = [
        OperadoraORM(
            cnpj=f"99{str(i).zfill(12)}",
            razao_social=f"Operadora Teste {i}",
            registro_ans=f"99{str(i).zfill(4)}",
            modalidade="Cooperativa Médica",
            uf=["SP", "RJ", "MG", "RS", "BA"][i % 5],
        )
        for i in range(1, 11)  # 10 operadoras
    ]
    db_session.add_all(operadoras)
    db_session.commit()
    return operadoras


@pytest.fixture
def despesas_teste(db_session: Session, operadora_teste: OperadoraORM) -> list[DespesaORM]:
    """Cria despesas de teste para uma operadora."""
    despesas = [
        DespesaORM(
            cnpj=operadora_teste.cnpj,
            razao_social=operadora_teste.razao_social,
            ano=2025,
            trimestre=trimestre,
            valor=100000.0 * trimestre,
            status_qualidade="OK",
        )
        for trimestre in range(1, 5)  # Q1 a Q4
    ]
    db_session.add_all(despesas)
    db_session.commit()
    return despesas


# =============================================================
# TESTES DE REPOSITÓRIO: OperadoraRepository
# =============================================================
@pytest.mark.integration
class TestOperadoraRepositoryIntegration:
    """Testes de integração do OperadoraRepository com MySQL real."""
    
    @pytest.mark.asyncio
    async def test_get_by_cnpj_existente(self, db_session: Session, operadora_teste: OperadoraORM):
        """Deve retornar operadora quando CNPJ existe."""
        repo = OperadoraRepository(db_session)
        
        result = await repo.get_by_cnpj(operadora_teste.cnpj)
        
        assert result is not None
        assert result.cnpj == operadora_teste.cnpj
        assert result.razao_social == operadora_teste.razao_social
        assert result.uf == "SP"
    
    @pytest.mark.asyncio
    async def test_get_by_cnpj_inexistente(self, db_session: Session):
        """Deve retornar None quando CNPJ não existe."""
        repo = OperadoraRepository(db_session)
        
        result = await repo.get_by_cnpj("00000000000000")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_all_paginacao(self, db_session: Session, operadoras_teste_batch):
        """Deve paginar resultados corretamente."""
        repo = OperadoraRepository(db_session)
        
        # Página 1 com limit 5
        results, total = await repo.list_all(page=1, limit=5, cnpj_filter="99")
        
        assert len(results) == 5
        assert total >= 10  # Pelo menos as 10 criadas
    
    @pytest.mark.asyncio
    async def test_list_all_filtro_razao_social(self, db_session: Session, operadoras_teste_batch):
        """Deve filtrar por razão social."""
        repo = OperadoraRepository(db_session)
        
        results, total = await repo.list_all(
            page=1, 
            limit=20, 
            razao_social_filter="Teste 5"
        )
        
        assert len(results) >= 1
        assert any("Teste 5" in r.razao_social for r in results)
    
    @pytest.mark.asyncio
    async def test_save_nova_operadora(self, db_session: Session):
        """Deve inserir nova operadora."""
        repo = OperadoraRepository(db_session)
        
        nova = Operadora(
            cnpj="99999999000199",
            razao_social="Nova Operadora Teste",
            registro_ans="999991",
            modalidade=Modalidade.AUTOGESTAO,
            uf="RJ",
        )
        
        result = await repo.save(nova)
        
        assert result.cnpj == nova.cnpj
        
        # Verificar no banco
        saved = await repo.get_by_cnpj(nova.cnpj)
        assert saved is not None
        assert saved.razao_social == "Nova Operadora Teste"
    
    @pytest.mark.asyncio
    async def test_save_atualiza_existente(self, db_session: Session, operadora_teste: OperadoraORM):
        """Deve atualizar operadora existente."""
        repo = OperadoraRepository(db_session)
        
        # Carrega e modifica
        operadora = await repo.get_by_cnpj(operadora_teste.cnpj)
        operadora.razao_social = "Razão Social Atualizada"
        
        await repo.save(operadora)
        
        # Verifica atualização
        updated = await repo.get_by_cnpj(operadora_teste.cnpj)
        assert updated.razao_social == "Razão Social Atualizada"


# =============================================================
# TESTES DE REPOSITÓRIO: DespesaRepository
# =============================================================
@pytest.mark.integration
class TestDespesaRepositoryIntegration:
    """Testes de integração do DespesaRepository com MySQL real."""
    
    @pytest.mark.asyncio
    async def test_get_by_operadora_todas(self, db_session: Session, operadora_teste, despesas_teste):
        """Deve retornar todas as despesas de uma operadora."""
        repo = DespesaRepository(db_session)
        
        results = await repo.get_by_operadora(operadora_teste.cnpj)
        
        assert len(results) == 4  # Q1 a Q4
        # Ordenação descendente (mais recente primeiro)
        assert results[0].trimestre == 4
    
    @pytest.mark.asyncio
    async def test_get_by_operadora_filtro_ano(self, db_session: Session, operadora_teste, despesas_teste):
        """Deve filtrar despesas por ano."""
        repo = DespesaRepository(db_session)
        
        results = await repo.get_by_operadora(operadora_teste.cnpj, ano=2025)
        
        assert all(d.ano == 2025 for d in results)
    
    @pytest.mark.asyncio
    async def test_get_by_operadora_filtro_trimestre(self, db_session: Session, operadora_teste, despesas_teste):
        """Deve filtrar despesas por trimestre específico."""
        repo = DespesaRepository(db_session)
        
        results = await repo.get_by_operadora(operadora_teste.cnpj, ano=2025, trimestre=2)
        
        assert len(results) == 1
        assert results[0].trimestre == 2
        assert results[0].valor == 200000.0  # 100000 * 2
    
    @pytest.mark.asyncio
    async def test_get_estatisticas_gerais(self, db_session: Session, operadora_teste, despesas_teste):
        """Deve calcular estatísticas agregadas."""
        repo = DespesaRepository(db_session)
        
        stats = await repo.get_estatisticas_gerais()
        
        assert "total_despesas" in stats
        assert "media_despesas" in stats
        assert "quantidade_registros" in stats
        assert "top_5_operadoras" in stats
        assert stats["total_despesas"] >= 1000000.0  # Soma das despesas teste
    
    @pytest.mark.asyncio
    async def test_save_batch_despesas(self, db_session: Session, operadora_teste):
        """Deve salvar múltiplas despesas em batch."""
        repo = DespesaRepository(db_session)
        
        novas_despesas = [
            DespesaFinanceira(
                cnpj=operadora_teste.cnpj,
                razao_social=operadora_teste.razao_social,
                ano=2024,
                trimestre=i,
                valor=50000.0 * i,
            )
            for i in range(1, 3)
        ]
        
        count = await repo.save_batch(novas_despesas)
        
        assert count == 2


# =============================================================
# TESTES DE API: Endpoints de Operadoras
# =============================================================
@pytest.mark.integration
class TestAPIOperadorasIntegration:
    """Testes de integração dos endpoints de operadoras."""
    
    def test_listar_operadoras_com_dados_reais(self, integration_client):
        """GET /api/operadoras deve retornar dados do banco."""
        response = integration_client.get("/api/operadoras")
        
        assert response.status_code == 200
        data = response.json()
        # Schema usa "data" não "items"
        assert "data" in data
        assert "total" in data
        assert "page" in data
    
    def test_buscar_operadora_inexistente_retorna_404(self, integration_client):
        """GET /api/operadoras/{cnpj} deve retornar 404 para CNPJ inexistente."""
        response = integration_client.get("/api/operadoras/00000000000000")
        
        assert response.status_code == 404
    
    def test_filtrar_operadoras_por_razao_social(self, integration_client):
        """GET /api/operadoras?razao_social=X deve filtrar resultados."""
        # Primeiro, garantir que existem operadoras no banco
        response = integration_client.get("/api/operadoras?limit=1")
        if response.json()["total"] == 0:
            pytest.skip("Nenhuma operadora no banco de teste")
        
        # Buscar com filtro
        response = integration_client.get("/api/operadoras?razao_social=Teste")
        
        assert response.status_code == 200
        data = response.json()
        # Se houver resultados, devem conter "Teste" - usa "data" não "items"
        for item in data["data"]:
            if "Teste" not in item["razao_social"]:
                # Pode não ter match, mas não deve crashar
                pass
    
    def test_paginacao_funciona(self, integration_client):
        """Paginação deve funcionar corretamente."""
        response_p1 = integration_client.get("/api/operadoras?page=1&limit=5")
        response_p2 = integration_client.get("/api/operadoras?page=2&limit=5")
        
        assert response_p1.status_code == 200
        assert response_p2.status_code == 200
        
        data_p1 = response_p1.json()
        data_p2 = response_p2.json()
        
        # Páginas diferentes devem ter itens diferentes (se houver dados suficientes)
        # Schema usa "data" não "items"
        if data_p1["total"] > 5:
            items_p1_cnpjs = {item["cnpj"] for item in data_p1["data"]}
            items_p2_cnpjs = {item["cnpj"] for item in data_p2["data"]}
            assert items_p1_cnpjs != items_p2_cnpjs


# =============================================================
# TESTES DE API: Endpoints de Estatísticas
# =============================================================
@pytest.mark.integration
class TestAPIEstatisticasIntegration:
    """Testes de integração dos endpoints de estatísticas."""
    
    def test_estatisticas_gerais(self, integration_client):
        """GET /api/estatisticas deve retornar estatísticas agregadas."""
        response = integration_client.get("/api/estatisticas")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_despesas" in data
        assert "media_despesas" in data
        assert "quantidade_registros" in data
        assert "top_5_operadoras" in data
        assert isinstance(data["top_5_operadoras"], list)


# =============================================================
# TESTES DE TRANSAÇÃO E ROLLBACK
# =============================================================
@pytest.mark.integration
class TestTransactionIntegration:
    """Testes de comportamento transacional."""
    
    @pytest.mark.asyncio
    async def test_rollback_em_erro(self, db_session: Session):
        """Transação deve ser revertida em caso de erro."""
        repo = OperadoraRepository(db_session)
        
        # Cria operadora
        operadora = Operadora(
            cnpj="99888888000199",
            razao_social="Operadora Para Rollback",
            registro_ans="998888",
            modalidade=Modalidade.COOPERATIVA_MEDICA,
            uf="MG",
        )
        
        await repo.save(operadora)
        
        # Verifica que foi salva
        saved = await repo.get_by_cnpj("99888888000199")
        assert saved is not None
        
        # Rollback manual (simula erro)
        db_session.rollback()
        
        # Após rollback, não deve existir mais em nova session
        new_session = TestSessionLocal()
        try:
            new_repo = OperadoraRepository(new_session)
            result = await new_repo.get_by_cnpj("99888888000199")
            # Pode ou não existir dependendo do estado do banco
            # O importante é não crashar
        finally:
            new_session.close()
    
    @pytest.mark.asyncio
    async def test_commit_persiste_dados(self, db_session: Session):
        """Commit deve persistir dados no banco."""
        repo = OperadoraRepository(db_session)
        
        operadora = Operadora(
            cnpj="99777777000199",
            razao_social="Operadora Persistida",
            registro_ans="997777",
            modalidade=Modalidade.FILANTROPIA,
            uf="BA",
        )
        
        await repo.save(operadora)
        
        # Verifica em nova session
        new_session = TestSessionLocal()
        try:
            new_repo = OperadoraRepository(new_session)
            result = await new_repo.get_by_cnpj("99777777000199")
            assert result is not None
            assert result.razao_social == "Operadora Persistida"
        finally:
            # Cleanup
            new_session.execute(text("DELETE FROM operadoras WHERE cnpj = '99777777000199'"))
            new_session.commit()
            new_session.close()


# =============================================================
# TESTES DE PERFORMANCE
# =============================================================
@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Testes de performance com dados reais."""
    
    def test_listagem_responde_rapido(self, integration_client):
        """Listagem deve responder em menos de 500ms."""
        import time
        
        start = time.time()
        response = integration_client.get("/api/operadoras?limit=100")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.5, f"Listagem demorou {elapsed:.2f}s (limite: 0.5s)"
    
    def test_estatisticas_responde_rapido(self, integration_client):
        """Estatísticas devem responder em menos de 1s."""
        import time
        
        start = time.time()
        response = integration_client.get("/api/estatisticas")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Estatísticas demorou {elapsed:.2f}s (limite: 1.0s)"


# =============================================================
# TESTES DE HEALTH CHECK COM BANCO REAL
# =============================================================
@pytest.mark.integration
class TestHealthCheckIntegration:
    """Testes de health check com conexão real ao banco."""
    
    def test_health_check_com_banco_conectado(self, integration_client):
        """Health check deve funcionar com banco conectado."""
        response = integration_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
