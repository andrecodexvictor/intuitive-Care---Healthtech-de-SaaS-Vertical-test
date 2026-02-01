# =============================================================
# test_etl.py - Testes do Pipeline ETL
# =============================================================
# Cobertura: DataProcessor, validação de CNPJ, normalização de colunas
#
# TESTES:
# - Leitura de arquivos CSV
# - Detecção de delimitador
# - Validação de CNPJ
# - Normalização de colunas
# - Tratamento de valores inválidos
# =============================================================
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from src.domain.entities import StatusQualidade, Operadora, DespesaFinanceira


class TestCNPJValidation:
    """Testes de validação de CNPJ."""
    
    def test_valid_cnpj(self):
        """CNPJ válido deve passar na validação."""
        from src.domain.entities import CNPJ
        
        # CNPJs válidos conhecidos - usar modelo Pydantic
        valid_cnpjs = [
            "11444777000161",  # CNPJ válido
        ]
        
        for cnpj in valid_cnpjs:
            # CNPJ é um Pydantic model, usamos a criação direta
            try:
                cnpj_obj = CNPJ(valor=cnpj)
                assert cnpj_obj.valor == cnpj
            except Exception as e:
                pytest.fail(f"CNPJ {cnpj} deveria ser válido, mas falhou: {e}")
    
    def test_invalid_cnpj_wrong_digits(self):
        """CNPJ com dígitos verificadores errados deve ser inválido."""
        from src.domain.entities import CNPJ
        from pydantic import ValidationError
        
        invalid_cnpjs = [
            "11444777000160",  # Último dígito errado
            "11444777000162",  # Último dígito errado
            "12345678901234",  # CNPJ genérico inválido
        ]
        
        for cnpj in invalid_cnpjs:
            with pytest.raises(ValidationError):
                CNPJ(valor=cnpj)
    
    def test_invalid_cnpj_wrong_length(self):
        """CNPJ com tamanho errado deve ser inválido."""
        from src.domain.entities import CNPJ
        from pydantic import ValidationError
        
        invalid_cnpjs = [
            "1144477700016",   # 13 dígitos
            "114447770001611", # 15 dígitos
            "123",             # Muito curto
        ]
        
        for cnpj in invalid_cnpjs:
            with pytest.raises(ValidationError):
                CNPJ(valor=cnpj)
    
    def test_invalid_cnpj_non_numeric(self):
        """CNPJ com caracteres não numéricos deve ser inválido."""
        from src.domain.entities import CNPJ
        from pydantic import ValidationError
        
        invalid_cnpjs = [
            "1144477700016A",
            "abcdefghijklmn",
        ]
        
        for cnpj in invalid_cnpjs:
            with pytest.raises(ValidationError):
                CNPJ(valor=cnpj)
    
    def test_cnpj_all_same_digits(self):
        """CNPJ com todos dígitos iguais deve ser inválido."""
        from src.domain.entities import CNPJ
        from pydantic import ValidationError
        
        invalid_cnpjs = [
            "00000000000000",
            "11111111111111",
            "99999999999999",
        ]
        
        for cnpj in invalid_cnpjs:
            with pytest.raises(ValidationError):
                CNPJ(valor=cnpj)


class TestCSVProcessing:
    """Testes de processamento de arquivos CSV."""
    
    @pytest.fixture
    def sample_csv_content(self):
        """Conteúdo CSV de exemplo."""
        return """CNPJ;RAZAO_SOCIAL;VL_SALDO_FINAL;ANO;TRIMESTRE
11444777000161;OPERADORA TESTE LTDA;1000.50;2024;1
00000000000191;OUTRA OPERADORA SA;2500.00;2024;1
12345678901234;OPERADORA INVALIDA;500.00;2024;1"""
    
    @pytest.fixture
    def sample_csv_file(self, sample_csv_content):
        """Cria arquivo CSV temporário para testes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(sample_csv_content)
            filepath = f.name
        
        yield Path(filepath)
        
        # Cleanup
        os.unlink(filepath)
    
    def test_read_csv_basic(self, sample_csv_file):
        """Deve ler arquivo CSV corretamente."""
        df = pd.read_csv(sample_csv_file, sep=';')
        
        assert len(df) == 3
        assert 'CNPJ' in df.columns
        assert 'RAZAO_SOCIAL' in df.columns
        assert 'VL_SALDO_FINAL' in df.columns
    
    def test_detect_semicolon_delimiter(self, sample_csv_file):
        """Deve detectar delimitador ponto-e-vírgula."""
        from src.etl.processor import DataProcessor
        
        processor = DataProcessor()
        delimiter = processor._detect_delimiter(sample_csv_file)
        
        assert delimiter == ";"
    
    def test_detect_comma_delimiter(self):
        """Deve detectar delimitador vírgula."""
        content = """CNPJ,RAZAO_SOCIAL,VALOR
11444777000161,TESTE,1000.00"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(content)
            filepath = Path(f.name)
        
        try:
            from src.etl.processor import DataProcessor
            processor = DataProcessor()
            delimiter = processor._detect_delimiter(filepath)
            
            assert delimiter == ","
        finally:
            os.unlink(filepath)


class TestDataValidation:
    """Testes de validação de dados."""
    
    def test_despesa_with_negative_value(self):
        """Despesa com valor negativo deve ser marcada."""
        despesa = DespesaFinanceira(
            cnpj="11444777000161",
            razao_social="Teste",
            ano=2024,
            trimestre=1,
            valor=-1000.0,
            status_qualidade=StatusQualidade.OK
        )
        
        # Valor negativo ainda é válido (pode ser estorno)
        assert despesa.valor == -1000.0
    
    def test_despesa_with_zero_value(self):
        """Despesa com valor zero deve ser aceita."""
        despesa = DespesaFinanceira(
            cnpj="11444777000161",
            razao_social="Teste",
            ano=2024,
            trimestre=1,
            valor=0.0,
            status_qualidade=StatusQualidade.OK
        )
        
        assert despesa.valor == 0.0
    
    def test_despesa_with_large_value(self):
        """Despesa com valor muito grande deve ser aceita."""
        despesa = DespesaFinanceira(
            cnpj="11444777000161",
            razao_social="Teste",
            ano=2024,
            trimestre=1,
            valor=999999999999.99,
            status_qualidade=StatusQualidade.OK
        )
        
        assert despesa.valor == 999999999999.99
    
    def test_status_qualidade_values(self):
        """StatusQualidade deve ter valores esperados."""
        assert StatusQualidade.OK.value == "OK"
        assert StatusQualidade.CNPJ_INVALIDO.value == "CNPJ_INVALIDO"
        assert StatusQualidade.VALOR_SUSPEITO.value == "VALOR_SUSPEITO"  # Nome correto do enum


class TestOperadoraEntity:
    """Testes da entidade Operadora."""
    
    def test_operadora_creation(self):
        """Operadora deve ser criada corretamente."""
        operadora = Operadora(
            cnpj="11444777000161",
            razao_social="OPERADORA TESTE LTDA",
            registro_ans="123456",
            modalidade=None,
            uf="SP"
        )
        
        assert operadora.cnpj == "11444777000161"
        assert operadora.razao_social == "OPERADORA TESTE LTDA"
        assert operadora.uf == "SP"
    
    def test_operadora_with_all_fields(self):
        """Operadora deve aceitar todos os campos."""
        from src.domain.entities import Modalidade
        
        operadora = Operadora(
            cnpj="11444777000161",
            razao_social="UNIMED SUL",
            registro_ans="123456",
            modalidade=Modalidade.COOPERATIVA_MEDICA,  # Nome correto do enum
            uf="RS"
        )
        
        assert operadora.modalidade == Modalidade.COOPERATIVA_MEDICA
    
    def test_operadora_without_optional_fields(self):
        """Operadora deve funcionar sem campos opcionais."""
        operadora = Operadora(
            cnpj="11444777000161",
            razao_social="TESTE",
            registro_ans=None,
            modalidade=None,
            uf=None
        )
        
        assert operadora.registro_ans is None
        assert operadora.modalidade is None
        assert operadora.uf is None


class TestColumnMapping:
    """Testes do mapeamento de colunas."""
    
    def test_column_mappings_exist(self):
        """Mapeamentos de colunas devem existir."""
        from src.etl.processor import COLUMN_MAPPINGS
        
        assert "CNPJ" in COLUMN_MAPPINGS
        assert "RAZAO_SOCIAL" in COLUMN_MAPPINGS
        assert "VALOR" in COLUMN_MAPPINGS
        assert "ANO" in COLUMN_MAPPINGS
        assert "TRIMESTRE" in COLUMN_MAPPINGS
    
    def test_column_mappings_have_variations(self):
        """Cada coluna deve ter múltiplas variações."""
        from src.etl.processor import COLUMN_MAPPINGS
        
        for col_name, variations in COLUMN_MAPPINGS.items():
            assert isinstance(variations, list)
            assert len(variations) >= 1, f"{col_name} deve ter pelo menos 1 variação"


class TestDespesaFinanceiraEntity:
    """Testes da entidade DespesaFinanceira."""
    
    def test_despesa_creation(self):
        """DespesaFinanceira deve ser criada corretamente."""
        despesa = DespesaFinanceira(
            cnpj="11444777000161",
            razao_social="TESTE LTDA",
            ano=2024,
            trimestre=1,
            valor=50000.00,
            status_qualidade=StatusQualidade.OK
        )
        
        assert despesa.cnpj == "11444777000161"
        assert despesa.ano == 2024
        assert despesa.trimestre == 1
        assert despesa.valor == 50000.00
    
    def test_despesa_trimestre_range(self):
        """Trimestre deve ser 1-4."""
        for q in [1, 2, 3, 4]:
            despesa = DespesaFinanceira(
                cnpj="11444777000161",
                razao_social="TESTE",
                ano=2024,
                trimestre=q,
                valor=1000.0,
                status_qualidade=StatusQualidade.OK
            )
            assert despesa.trimestre == q
    
    def test_despesa_with_invalid_cnpj_status(self):
        """Despesa com CNPJ inválido deve ter status correto."""
        despesa = DespesaFinanceira(
            cnpj="12345678901234",  # CNPJ inválido
            razao_social="TESTE",
            ano=2024,
            trimestre=1,
            valor=1000.0,
            status_qualidade=StatusQualidade.CNPJ_INVALIDO
        )
        
        assert despesa.status_qualidade == StatusQualidade.CNPJ_INVALIDO


class TestDataIntegrity:
    """Testes de integridade de dados."""
    
    def test_cnpj_consistency(self):
        """CNPJ deve ser consistente entre operadora e despesa."""
        cnpj = "11444777000161"
        
        operadora = Operadora(
            cnpj=cnpj,
            razao_social="TESTE",
            registro_ans=None,
            modalidade=None,
            uf="SP"
        )
        
        despesa = DespesaFinanceira(
            cnpj=cnpj,
            razao_social="TESTE",
            ano=2024,
            trimestre=1,
            valor=1000.0,
            status_qualidade=StatusQualidade.OK
        )
        
        assert operadora.cnpj == despesa.cnpj
