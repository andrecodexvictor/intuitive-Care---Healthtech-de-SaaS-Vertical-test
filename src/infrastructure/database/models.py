# =============================================================
# models.py - ORM Models (Mapeamento Objeto-Relacional)
# =============================================================
# ARQUITETURA: Clean Architecture - Infraestrutura
#
# DIFERENÇA IMPORTANTE:
# - Entidades (domain/entities.py): Lógica de negócio, validação.
# - ORM Models (este arquivo): Mapeamento para tabelas SQL.
#
# POR QUE SEPARAR?
# - Entidades podem ter métodos de negócio complexos.
# - ORM Models focam em persistência e relacionamentos.
# - Facilita testes (não precisa de banco para testar entidades).
# - Permite diferentes "views" do mesmo dado.
#
# CONVERSÃO:
# - ORM Model -> Entidade: ORM.to_entity() ou Entidade.from_orm(orm)
# - Entidade -> ORM Model: ORM.from_entity(entidade)
# =============================================================
from sqlalchemy import Column, String, Integer, Float, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.infrastructure.database.connection import Base
from src.domain.entities import StatusQualidade, Modalidade, Operadora, DespesaFinanceira


class OperadoraORM(Base):
    """
    ORM Model para tabela 'operadoras'.
    
    DECISÃO DE NORMALIZAÇÃO:
    Optamos por tabela NORMALIZADA (uma tabela para operadoras,
    outra para despesas) ao invés de desnormalizada.
    
    JUSTIFICATIVA:
    - Razão social aparece 1x, não N vezes (uma por despesa).
    - Atualizações cadastrais são fáceis (UPDATE em 1 lugar).
    - Queries analíticas usam JOIN (performance OK com índices).
    - Dados de entrada parecem ter ~5000 operadoras (volume gerenciável).
    
    TRADE-OFF:
    - Desnormalizado seria mais simples para leitura.
    - Mas teríamos dados duplicados e inconsistência.
    """
    __tablename__ = "operadoras"
    
    # CNPJ como chave primária (é único por definição)
    # VARCHAR(14) sem formatação para facilitar JOINs
    cnpj = Column(String(14), primary_key=True, index=True)
    
    # Razão social pode ter até 200 caracteres
    razao_social = Column(String(200), nullable=False, index=True)
    
    # Registro ANS é opcional (pode não ter no arquivo consolidado)
    registro_ans = Column(String(6), nullable=True)
    
    # Modalidade como ENUM para garantir valores válidos
    # DECISÃO: Usar String ao invés de ENUM MySQL.
    # JUSTIFICATIVA: ENUMs MySQL são rígidos em alterações.
    # String com validação na aplicação é mais flexível.
    modalidade = Column(String(50), nullable=True)
    
    # UF com 2 caracteres (sigla do estado)
    uf = Column(String(2), nullable=True, index=True)
    
    # Relacionamento com despesas (1 operadora -> N despesas)
    despesas = relationship("DespesaORM", back_populates="operadora")
    
    def to_entity(self) -> Operadora:
        """Converte ORM Model para Entidade de Domínio."""
        modalidade_enum = None
        if self.modalidade:
            try:
                modalidade_enum = Modalidade(self.modalidade)
            except ValueError:
                modalidade_enum = Modalidade.DESCONHECIDA
        
        return Operadora(
            cnpj=self.cnpj,
            razao_social=self.razao_social,
            registro_ans=self.registro_ans,
            modalidade=modalidade_enum,
            uf=self.uf,
        )
    
    @classmethod
    def from_entity(cls, entity: Operadora) -> "OperadoraORM":
        """Cria ORM Model a partir de Entidade."""
        return cls(
            cnpj=entity.cnpj,
            razao_social=entity.razao_social,
            registro_ans=entity.registro_ans,
            modalidade=entity.modalidade.value if entity.modalidade else None,
            uf=entity.uf,
        )


class DespesaORM(Base):
    """
    ORM Model para tabela 'despesas'.
    
    TIPOS DE DADOS:
    - valor: FLOAT ao invés de DECIMAL.
    
    DECISÃO:
    Optamos por FLOAT(15, 2) ao invés de DECIMAL(15, 2).
    
    JUSTIFICATIVA:
    - Dados são para análise, não para contabilidade.
    - Precisão de centavos é suficiente para relatórios.
    - FLOAT é mais rápido para agregações.
    
    TRADE-OFF:
    - DECIMAL seria exato (sem erros de arredondamento).
    - Para sistema financeiro de produção, usaríamos DECIMAL.
    - Para análise estatística, FLOAT é aceitável.
    """
    __tablename__ = "despesas"
    
    # ID auto-incremento (não usamos CNPJ+período como PK composta
    # porque pode haver múltiplas despesas no mesmo período)
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # FK para operadora
    cnpj = Column(String(14), ForeignKey("operadoras.cnpj"), nullable=False, index=True)
    
    # Razão social DESNORMALIZADA aqui
    # DECISÃO: Manter razão social na despesa também.
    # JUSTIFICATIVA:
    # - O arquivo consolidado original tem razão social.
    # - Permite gerar CSV sem JOIN.
    # - Trade-off: alguma redundância, mas útil para export.
    razao_social = Column(String(200), nullable=True)
    
    # Período: ano + trimestre separados
    # DECISÃO: Colunas separadas ao invés de DATE.
    # JUSTIFICATIVA:
    # - Dados de origem são por trimestre, não data exata.
    # - Facilita GROUP BY ano, trimestre.
    # - Índice composto para queries por período.
    ano = Column(Integer, nullable=False)
    trimestre = Column(Integer, nullable=False)
    
    # Valor da despesa (pode ser negativo = estorno)
    valor = Column(Float, nullable=False)
    
    # Status de qualidade do dado
    status_qualidade = Column(String(20), nullable=False, default="OK")
    
    # Relacionamento com operadora
    operadora = relationship("OperadoraORM", back_populates="despesas")
    
    # ÍNDICES COMPOSTOS para queries analíticas
    __table_args__ = (
        # Índice para busca por período
        Index("idx_despesas_periodo", "ano", "trimestre"),
        # Índice para busca por operadora + período
        Index("idx_despesas_cnpj_periodo", "cnpj", "ano", "trimestre"),
    )
    
    def to_entity(self) -> DespesaFinanceira:
        """Converte ORM Model para Entidade."""
        try:
            status = StatusQualidade(self.status_qualidade)
        except ValueError:
            status = StatusQualidade.OK
        
        return DespesaFinanceira(
            id=self.id,
            cnpj=self.cnpj,
            razao_social=self.razao_social,
            ano=self.ano,
            trimestre=self.trimestre,
            valor=self.valor,
            status_qualidade=status,
        )
    
    @classmethod
    def from_entity(cls, entity: DespesaFinanceira) -> "DespesaORM":
        """Cria ORM Model a partir de Entidade."""
        return cls(
            cnpj=entity.cnpj,
            razao_social=entity.razao_social,
            ano=entity.ano,
            trimestre=entity.trimestre,
            valor=entity.valor,
            status_qualidade=entity.status_qualidade.value,
        )


class DespesaAgregadaORM(Base):
    """
    ORM Model para tabela 'despesas_agregadas'.
    
    Esta tabela armazena resultados PRÉ-CALCULADOS de agregações.
    
    DECISÃO: Criar tabela separada para agregações.
    JUSTIFICATIVA:
    - Queries de agregação podem ser lentas com muitos dados.
    - Pré-calculando, a API responde instantaneamente.
    - Atualização pode ser feita em batch (após nova ingestão).
    
    TRADE-OFF:
    - Dados podem ficar desatualizados se não recalcular.
    - Para este caso, é aceitável (dados trimestrais).
    """
    __tablename__ = "despesas_agregadas"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    razao_social = Column(String(200), nullable=False, index=True)
    uf = Column(String(2), nullable=True, index=True)
    total = Column(Float, nullable=False)
    media = Column(Float, nullable=False)
    desvio_padrao = Column(Float, nullable=False, default=0.0)
    quantidade_registros = Column(Integer, nullable=False, default=0)
    
    # Índice para ordenação por total
    __table_args__ = (
        Index("idx_agregadas_total", "total"),
    )
