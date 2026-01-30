# 🏥 API de Análise de Despesas de Operadoras de Saúde

> Solução para o Teste de Estágio da Intuitive Care

---

## 📋 Índice

1. [Visão Geral](#-visão-geral)
2. [Arquitetura](#-arquitetura)
3. [Stack Tecnológica](#-stack-tecnológica)
4. [Decisões de Design](#-decisões-de-design)
5. [Quick Start](#-quick-start)
6. [Endpoints da API](#-endpoints-da-api)
7. [Trade-offs](#-trade-offs)
8. [Estrutura do Projeto](#-estrutura-do-projeto)

---

## 🎯 Visão Geral

API REST para análise de despesas de operadoras de planos de saúde, consumindo dados públicos da ANS (Agência Nacional de Saúde Suplementar).

### Funcionalidades Implementadas

| Feature | Descrição |
|---------|-----------|
| **ETL Completo** | Download, extração, validação e persistência de dados da ANS |
| **API REST** | Endpoints para consulta de operadoras e despesas |
| **Paginação** | Listagem paginada com filtros flexíveis |
| **Estatísticas** | Agregações e rankings com cache em memória |
| **Validação de CNPJ** | Verificação completa dos dígitos verificadores |
| **Qualidade de Dados** | Marcação de registros problemáticos (sem remoção) |

---

## 🏗️ Arquitetura

Foi adotada a **Clean Architecture** por oferecer separação clara de responsabilidades e facilitar a manutenção a longo prazo:

```
┌─────────────────────────────────────────────────────────────┐
│                        INTERFACE                            │
│              (FastAPI Routers, Schemas)                     │
│   Responsabilidade: Receber HTTP, validar, retornar JSON    │
├─────────────────────────────────────────────────────────────┤
│                       APPLICATION                           │
│              (Interfaces, Use Cases)                        │
│   Responsabilidade: Orquestrar fluxo, definir contratos     │
├─────────────────────────────────────────────────────────────┤
│                         DOMAIN                              │
│              (Entities, Value Objects)                      │
│   Responsabilidade: Regras de negócio puras                 │
├─────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE                         │
│              (SQLAlchemy, MySQL, ETL)                       │
│   Responsabilidade: Implementações concretas                │
└─────────────────────────────────────────────────────────────┘
```

### Justificativas da Escolha Arquitetural

1. **Testabilidade**: A camada de Domain não possui dependências de frameworks externos, permitindo testes unitários puros sem necessidade de mocks complexos.

2. **Manutenibilidade**: Alterações no banco de dados (ex: migração para PostgreSQL) requerem modificações apenas na camada Infrastructure, sem impacto nas demais.

3. **Clareza de Responsabilidades**: Cada camada possui função bem definida, facilitando a navegação e entendimento do código.

4. **Evolução Independente**: Novos endpoints podem ser adicionados sem modificar a lógica de negócio, e vice-versa.

### Fluxo de Dependências

```
Interface → Application → Domain
        ↓
Infrastructure
```

- ✅ Interface importa Application e Domain
- ✅ Application importa apenas Domain
- ❌ Domain não possui dependências externas
- ❌ Application não importa Infrastructure (utiliza interfaces abstratas)

---

## 🛠️ Stack Tecnológica

### Justificativas das Escolhas

| Tecnologia | Alternativas Avaliadas | Justificativa da Escolha |
|------------|------------------------|--------------------------|
| **FastAPI** | Flask, Django REST | Documentação automática (Swagger/OpenAPI), validação nativa com Pydantic, suporte async nativo |
| **SQLAlchemy** | Peewee, Tortoise ORM | Maturidade do projeto (15+ anos), suporte a múltiplos bancos, grande comunidade |
| **MySQL 8.0** | PostgreSQL, SQLite | Maior familiaridade operacional, setup simplificado no Windows |
| **Pydantic V2** | Marshmallow, Cerberus | Integração nativa com FastAPI, validação via type hints, performance 10x superior à V1 |
| **Pandas** | Polars, DuckDB | API consolidada, suporte nativo a Excel/CSV, documentação extensa |
| **Loguru** | logging (stdlib) | API simplificada, output colorido, menor boilerplate |
| **PyMySQL** | mysqlclient | Pure Python (sem compilação), compatibilidade Windows nativa |

### Decisão: MySQL vs PostgreSQL

O **MySQL** foi escolhido pelos seguintes fatores:

1. **Experiência Operacional**: Maior familiaridade com administração e troubleshooting do MySQL
2. **Ambiente de Desenvolvimento**: Setup mais direto no Windows sem dependências de compilação
3. **Adequação ao Caso de Uso**: Para o volume de dados estimado (~10K registros), as features avançadas do PostgreSQL não seriam necessárias

Em cenários com queries analíticas mais complexas ou maior volume, PostgreSQL seria reconsiderado.

---

## 📐 Decisões de Design

### 1. Repository Pattern

Foi implementado o padrão Repository para abstrair o acesso a dados:

```python
# application/interfaces.py - Contrato abstrato
class IOperadoraRepository(ABC):
    @abstractmethod
    async def get_by_cnpj(self, cnpj: str) -> Optional[Operadora]:
        pass

# infrastructure/database/repositories.py - Implementação concreta
class OperadoraRepository(IOperadoraRepository):
    def __init__(self, db: Session):
        self.db = db
    
    async def get_by_cnpj(self, cnpj: str) -> Optional[Operadora]:
        # Implementação com SQLAlchemy
        ...
```

**Benefícios obtidos:**
- Facilita criação de mocks para testes unitários
- Permite substituição do banco de dados sem alteração das demais camadas
- Documenta claramente as operações de persistência necessárias

### 2. Paginação Offset-Based

| Critério | Offset | Cursor |
|----------|--------|--------|
| Complexidade | ✅ Simples | ❌ Maior |
| URL Compartilhável | ✅ `/operadoras?page=5` | ❌ `/operadoras?cursor=abc123` |
| Total de Páginas | ✅ Cálculo direto | ❌ Não trivial |
| Performance | ❌ Degrada com volume | ✅ Constante |

**Justificativa da escolha Offset:**
- Volume de dados gerenciável (~5000 operadoras)
- Dados atualizados trimestralmente (baixa volatilidade)
- Necessidade do frontend de exibir "Página X de Y"

Para volumes na casa de milhões com atualizações frequentes, cursor-based seria mais adequado.

### 3. Tratamento de Dados Inválidos

A estratégia adotada foi **manter registros inválidos com marcação de status**, ao invés de removê-los:

```python
class StatusQualidade(str, Enum):
    OK = "OK"                        # Registro válido
    CNPJ_INVALIDO = "CNPJ_INVALIDO"  # Dígitos verificadores incorretos
    VALOR_SUSPEITO = "VALOR_SUSPEITO" # Valor negativo ou fora do esperado
    SEM_CADASTRO = "SEM_CADASTRO"     # CNPJ não encontrado no cadastro ANS
```

**Justificativas:**
- Preservação de informação para análise posterior
- Possibilidade de análise de qualidade dos dados de origem
- Transparência no tratamento de edge cases
- Dados da ANS podem conter inconsistências legítimas

### 4. Cache In-Memory para Estatísticas

Foi implementado cache em memória com TTL de 15 minutos para queries de agregação:

```python
_cache_estatisticas = None
_cache_timestamp = None
CACHE_TTL_MINUTES = 15
```

**Justificativa (ao invés de Redis):**
- Aplicação em instância única
- Dados atualizados trimestralmente (cache de 15min é seguro)
- Redução de dependências externas

Em cenário de múltiplas instâncias, seria necessário migrar para Redis ou similar.

### 5. Desnormalização Controlada

O schema mantém `razao_social` duplicada entre tabelas:

```
operadoras (cnpj PK, razao_social, ...)
     ↓ 1:N
despesas (id PK, cnpj FK, razao_social, ...)
```

**Justificativa:**
- Arquivo original da ANS já contém razão social em cada registro
- Permite geração de CSV de exportação sem necessidade de JOIN
- Trade-off aceito: redundância controlada em favor de praticidade operacional

### 6. Separação entre Entities e ORM Models

Foram criados dois tipos de modelos:

```python
# domain/entities.py - Regras de negócio (Pydantic)
class Operadora(BaseModel):
    cnpj: str
    razao_social: str

# infrastructure/database/models.py - Mapeamento (SQLAlchemy)
class OperadoraORM(Base):
    __tablename__ = "operadoras"
    cnpj = Column(String(14), primary_key=True)
```

**Justificativas:**
- Entities podem conter métodos de negócio não aplicáveis a ORM
- Testes de domínio executam sem dependência de banco
- Permite representações diferentes para contextos distintos

---

## 🚀 Quick Start

### Pré-requisitos

- Python 3.9+
- MySQL 8.0+
- Git

### 1. Clone e Setup

```bash
git clone <repo_url>
cd estagio

# Ambiente virtual (Windows)
python -m venv venv
venv\Scripts\activate

# Dependências
pip install -r requirements.txt
```

### 2. Configuração do Banco

```bash
mysql -u root -p -e "CREATE DATABASE intuitive_care_test CHARACTER SET utf8mb4;"
```

Criar arquivo `.env`:
```env
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_USER=root
DATABASE_PASSWORD=sua_senha
DATABASE_NAME=intuitive_care_test
API_DEBUG=true
LOG_LEVEL=INFO
```

### 3. Execução

```bash
uvicorn src.main:app --reload --port 8000
```

### 4. Documentação

| Recurso | URL |
|---------|-----|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |

---

## 📡 Endpoints da API

### Lista Operadoras (paginado)
```http
GET /api/operadoras?page=1&limit=20&razao_social=UNIMED
```

### Detalhes de Operadora
```http
GET /api/operadoras/{cnpj}
```

### Histórico de Despesas
```http
GET /api/operadoras/{cnpj}/despesas?ano=2024&trimestre=1
```

### Estatísticas Gerais
```http
GET /api/estatisticas
```

### Distribuição por UF
```http
GET /api/estatisticas/distribuicao-uf
```

---

## ⚖️ Trade-offs

| Decisão | Benefício | Custo | Justificativa |
|---------|-----------|-------|---------------|
| MySQL | Setup simples, familiaridade | Menos features avançadas | Volume adequado ao caso |
| Offset pagination | Simplicidade, URLs compartilháveis | Performance com alto volume | ~5000 registros é gerenciável |
| Cache in-memory | Sem dependências extras | Não escala horizontal | Instância única |
| Manter dados inválidos | Preservação de informação | Requer filtros no frontend | Transparência prioritária |
| Razão social duplicada | Export CSV direto | Redundância | Praticidade operacional |

---

## 📁 Estrutura do Projeto

```
estagio/
├── src/
│   ├── config.py           # Configurações centralizadas
│   ├── main.py             # Entry point FastAPI
│   ├── domain/             # Entidades de negócio
│   ├── application/        # Contratos e interfaces
│   ├── infrastructure/     # SQLAlchemy, MySQL
│   ├── interface/          # FastAPI routers
│   └── etl/                # Pipeline de ingestão
├── sql/
│   └── schema.sql
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 👤 Autor

Desenvolvido como parte do processo seletivo para estágio na **Intuitive Care**.
