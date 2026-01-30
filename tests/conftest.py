# =============================================================
# conftest.py - Configuração Global de Testes
# =============================================================
# Pytest fixtures compartilhadas entre todos os testes
# =============================================================
import pytest
import sys
from pathlib import Path

# Adicionar src ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def anyio_backend():
    """Backend para testes assíncronos."""
    return "asyncio"


@pytest.fixture
def app():
    """Aplicação FastAPI para testes."""
    from src.main import app
    return app
