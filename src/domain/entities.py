# entities.py - Domain entities (Pydantic models)
# Modelos de negócio puros, separados dos ORM models e API schemas
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date
from enum import Enum


# =============================================================
# STATUS DE QUALIDADE DOS DADOS
# =============================================================
# DECISÃO: Usar Enum para status de qualidade.
# JUSTIFICATIVA: 
# - Evita "magic strings" espalhadas pelo código.
# - Autocompletar na IDE.
# - Fácil de estender se surgir novo status.
# =============================================================
class StatusQualidade(str, Enum):
    """Status de validação dos registros de dados."""
    OK = "OK"  # Dados válidos, sem problemas detectados
    CNPJ_INVALIDO = "CNPJ_INVALIDO"  # CNPJ falhou na validação de dígitos
    VALOR_SUSPEITO = "VALOR_SUSPEITO"  # Valor negativo, zero ou muito alto
    DUPLICADO = "DUPLICADO"  # Registro duplicado detectado
    SEM_CADASTRO = "SEM_CADASTRO"  # CNPJ não encontrado no cadastro ANS


class Modalidade(str, Enum):
    """Modalidade de operação da operadora (classificação ANS)."""
    COOPERATIVA_MEDICA = "Cooperativa Médica"
    MEDICINA_GRUPO = "Medicina de Grupo"
    SEGURADORA = "Seguradora Especializada em Saúde"
    FILANTROPIA = "Filantropia"
    AUTOGESTAO = "Autogestão"
    ADMINISTRADORA = "Administradora de Benefícios"
    COOPERATIVA_ODONTO = "Cooperativa Odontológica"
    ODONTO_GRUPO = "Odontologia de Grupo"
    DESCONHECIDA = "Desconhecida"


# =============================================================
# VALUE OBJECTS
# =============================================================
class CNPJ(BaseModel):
    """
    Value Object para CNPJ com validação de dígitos verificadores.
    Normaliza formato (apenas 14 dígitos numéricos).
    """
    valor: str = Field(..., min_length=14, max_length=14, pattern=r"^\d{14}$")
    
    @field_validator("valor")
    @classmethod
    def validar_cnpj(cls, v: str) -> str:
        """Valida dígitos verificadores do CNPJ (algoritmo módulo 11)."""
        # Remove formatação se houver (pontos, barras, hífens)
        numeros = "".join(c for c in v if c.isdigit())
        
        if len(numeros) != 14:
            raise ValueError("CNPJ deve ter exatamente 14 dígitos")
        
        # Verifica se não é sequência repetida (ex: 11111111111111)
        if len(set(numeros)) == 1:
            raise ValueError("CNPJ inválido: sequência repetida")
        
        # Calcula primeiro dígito verificador
        pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(d) * p for d, p in zip(numeros[:12], pesos_1))
        resto = soma % 11
        digito_1 = 0 if resto < 2 else 11 - resto
        
        # Calcula segundo dígito verificador
        pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(d) * p for d, p in zip(numeros[:13], pesos_2))
        resto = soma % 11
        digito_2 = 0 if resto < 2 else 11 - resto
        
        # Verifica se os dígitos calculados batem com os informados
        if int(numeros[12]) != digito_1 or int(numeros[13]) != digito_2:
            raise ValueError("CNPJ inválido: dígitos verificadores incorretos")
        
        return numeros
    
    def formatado(self) -> str:
        """Retorna CNPJ formatado: XX.XXX.XXX/XXXX-XX"""
        v = self.valor
        return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
    
    def __str__(self) -> str:
        return self.valor
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, CNPJ):
            return self.valor == other.valor
        if isinstance(other, str):
            return self.valor == other
        return False
    
    def __hash__(self) -> int:
        return hash(self.valor)


class Periodo(BaseModel):
    """Período trimestral: ano (YYYY) + trimestre (1-4)."""
    ano: int = Field(..., ge=2000, le=2100)
    trimestre: int = Field(..., ge=1, le=4)
    
    def __str__(self) -> str:
        return f"{self.ano}-Q{self.trimestre}"
    
    def __lt__(self, other: "Periodo") -> bool:
        """Permite ordenação: Periodo(2023, 4) < Periodo(2024, 1)"""
        return (self.ano, self.trimestre) < (other.ano, other.trimestre)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Periodo):
            return self.ano == other.ano and self.trimestre == other.trimestre
        return False
    
    def __hash__(self) -> int:
        return hash((self.ano, self.trimestre))


# =============================================================
# ENTIDADES PRINCIPAIS
# =============================================================
class Operadora(BaseModel):
    """
    Entidade: Operadora de Plano de Saúde.
    
    Representa uma empresa que comercializa planos de saúde,
    registrada na ANS (Agência Nacional de Saúde Suplementar).
    
    CAMPOS:
    - cnpj: Identificador único (Cadastro Nacional da Pessoa Jurídica)
    - razao_social: Nome oficial da empresa
    - registro_ans: Código de registro na ANS (6 dígitos)
    - modalidade: Tipo de operação (Cooperativa, Seguradora, etc.)
    - uf: Estado sede da operadora
    """
    cnpj: str = Field(..., min_length=14, max_length=14, description="CNPJ da operadora")
    razao_social: str = Field(..., min_length=1, max_length=200, description="Nome oficial")
    registro_ans: Optional[str] = Field(None, max_length=6, description="Registro na ANS")
    modalidade: Optional[Modalidade] = Field(None, description="Modalidade de operação")
    uf: Optional[str] = Field(None, max_length=2, description="UF da sede")
    
    class Config:
        """Configuração do Pydantic para esta entidade."""
        from_attributes = True  # Permite criar de ORM models (ex: from_orm)
        frozen = False  # Permite mutação (pode mudar para True se quiser imutável)


class DespesaFinanceira(BaseModel):
    """
    Entidade: Despesa Financeira de uma Operadora.
    
    Representa um registro de despesa com eventos/sinistros
    de uma operadora em um determinado período (trimestre).
    
    CAMPOS:
    - cnpj: CNPJ da operadora (FK)
    - ano: Ano do registro (YYYY)
    - trimestre: Trimestre (1-4)
    - valor: Valor da despesa em reais (pode ser negativo = estorno)
    - status_qualidade: Flag indicando qualidade do dado
    
    TRADE-OFF (valor negativo):
    DECISÃO: Manter valores negativos, marcar como "VALOR_SUSPEITO".
    JUSTIFICATIVA: Valores negativos podem ser estornos legítimos.
    Removê-los perderia informação. Melhor manter e destacar.
    """
    id: Optional[int] = Field(None, description="ID interno (gerado pelo banco)")
    cnpj: str = Field(..., min_length=14, max_length=14, description="CNPJ da operadora")
    razao_social: Optional[str] = Field(None, description="Razão social (desnormalizado p/ CSV)")
    ano: int = Field(..., ge=2000, le=2100, description="Ano do registro")
    trimestre: int = Field(..., ge=1, le=4, description="Trimestre (1-4)")
    valor: float = Field(..., description="Valor da despesa em R$")
    status_qualidade: StatusQualidade = Field(
        default=StatusQualidade.OK,
        description="Status de qualidade do registro"
    )
    
    @field_validator("valor")
    @classmethod
    def validar_valor(cls, v: float) -> float:
        """
        Valida o valor da despesa.
        
        NÃO rejeita valores negativos, mas loga warning.
        A marcação de status é feita pelo serviço de validação.
        """
        # Aqui apenas garantimos que é um número válido
        if not isinstance(v, (int, float)):
            raise ValueError("Valor deve ser numérico")
        return float(v)
    
    @property
    def periodo(self) -> Periodo:
        """Retorna o período como Value Object."""
        return Periodo(ano=self.ano, trimestre=self.trimestre)
    
    class Config:
        from_attributes = True


class DespesaAgregada(BaseModel):
    """
    Entidade: Despesa Agregada por Operadora/UF.
    
    Resultado de agregação das despesas individuais,
    agrupadas por razão social e UF.
    
    CAMPOS CALCULADOS:
    - total: SUM(valor)
    - media: AVG(valor) por trimestre
    - desvio_padrao: STD(valor) - indica variabilidade
    """
    razao_social: str = Field(..., description="Razão social da operadora")
    uf: Optional[str] = Field(None, description="UF da operadora")
    total: float = Field(..., description="Total de despesas (soma)")
    media: float = Field(..., description="Média de despesas por trimestre")
    desvio_padrao: float = Field(default=0.0, description="Desvio padrão das despesas")
    quantidade_registros: int = Field(default=0, description="Qtd de registros agregados")
    
    class Config:
        from_attributes = True
