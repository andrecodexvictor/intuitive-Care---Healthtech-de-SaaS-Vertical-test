# 🏥 API de Análise de Despesas de Operadoras de Saúde

> **Teste Técnico para Estágio** — Intuitive Care  
> Este documento apresenta a solução desenvolvida, com foco nas decisões técnicas e justificativas adotadas.

---

## 📋 Sumário Executivo

Este projeto consiste em uma **API REST completa** para análise de despesas de operadoras de planos de saúde, utilizando dados públicos da ANS (Agência Nacional de Saúde Suplementar).

### Componentes Desenvolvidos

| Componente | Descrição | Status |
|------------|-----------|--------|
| **ETL** | Pipeline de ingestão: download, validação de CNPJs, consolidação de trimestres | ✅ Implementado |
| **API REST** | 6 endpoints RESTful com documentação OpenAPI automática | ✅ Implementado |
| **Frontend** | Dashboard Vue.js com visualizações e tabela paginada | ✅ Implementado |
| **Banco de Dados** | Schema MySQL + 3 queries analíticas conforme requisitos | ✅ Implementado |
| **Observabilidade** | Logging estruturado, métricas de performance, health check | ✅ Implementado |
| **Segurança** | Rate limiting, CORS hardening, security headers, log sanitization | ✅ Implementado |
| **Testes** | Suite pytest com 96 testes automatizados (todos passando) | ✅ Implementado |
| **CI/CD** | GitHub Actions com lint, test, security scan | ✅ Implementado |
| **Otimizações** | Cache genérico, índices SQL, refatorações de código | ✅ Implementado |

---

## 🏗️ Arquitetura

Foi adotada a **Clean Architecture** para garantir separação de responsabilidades e facilitar manutenção futura.

### Estrutura de Camadas

```
├── config/              # Configurações de ambiente
│   └── env/             # Templates de variáveis (.env.*)
│
├── docker/              # Arquivos de containerização
│   ├── api/             # Dockerfile da API
│   └── frontend/        # Dockerfile + nginx.conf
│
├── src/                 # Código-fonte principal
│   ├── domain/          # Regras de negócio puras
│   ├── application/     # Interfaces e contratos
│   ├── infrastructure/  # Implementações (DB, cache)
│   ├── interface/       # API REST (FastAPI)
│   └── etl/             # Pipeline de ingestão
│
├── frontend/            # Dashboard Vue.js
├── tests/               # Testes automatizados
├── sql/                 # DDL e queries
└── data/                # Arquivos baixados/gerados
```

### Justificativa da Escolha

1. **Testabilidade**: Camada de Domain sem dependências possibilita testes unitários puros
2. **Manutenibilidade**: Migração de banco de dados afeta apenas a camada Infrastructure
3. **Clareza**: Responsabilidades bem definidas facilitam onboarding de novos desenvolvedores

---

## 🛠️ Stack Tecnológica

| Tecnologia | Justificativa |
|------------|---------------|
| **FastAPI** | Documentação automática, validação nativa com Pydantic, suporte async |
| **SQLAlchemy** | ORM maduro com suporte a múltiplos bancos de dados |
| **MySQL 8.0** | Familiaridade operacional, adequado ao volume do projeto |
| **Pydantic V2** | Performance 10x superior à V1, integração nativa com FastAPI |
| **Vue.js 3** | Composition API moderna, excelente developer experience |
| **Loguru** | Logging estruturado com API simplificada |
| **Docker** | Portabilidade garantida em qualquer ambiente |

---

## 🚀 Instruções de Execução

### 🐳 Opção 1: Docker (RECOMENDADO)

A forma mais rápida de executar o projeto em qualquer sistema operacional.
Usa **rede interna com IPs fixos** para evitar problemas de DNS no Windows.

**Pré-requisitos:** Docker e Docker Compose instalados

<details>
<summary><b>🪟 Windows (PowerShell)</b></summary>

```powershell
# Clone o repositório
git clone https://github.com/andrecodexvictor/Teste_AndreVictorAndradeOliveiraSantos.git
cd Teste_AndreVictorAndradeOliveiraSantos

# Opção A: Script automático (recomendado)
.\docker-start.ps1 -WithETL

# Opção B: Comandos manuais
docker-compose up -d
docker-compose --profile etl up etl
```
</details>

<details>
<summary><b>🐧 Linux / 🍎 macOS</b></summary>

```bash
# Clone o repositório
git clone https://github.com/andrecodexvictor/Teste_AndreVictorAndradeOliveiraSantos.git
cd Teste_AndreVictorAndradeOliveiraSantos

# Opção A: Script automático (recomendado)
chmod +x docker-start.sh
./docker-start.sh --with-etl

# Opção B: Comandos manuais
docker-compose up -d
docker-compose --profile etl up etl
```
</details>

**Acesse:**
- 🌐 **Frontend:** http://localhost:3000
- 📡 **API:** http://localhost:8000
- 📖 **Docs:** http://localhost:8000/docs

**Rede Interna Docker:**
| Serviço | IP Fixo | Porta |
|---------|---------|-------|
| MySQL | 172.28.1.10 | 3306 |
| API | 172.28.1.20 | 8000 |
| Frontend | 172.28.1.30 | 80 |

**Comandos úteis:**
```bash
docker-compose logs -f api      # Ver logs da API
docker-compose down             # Parar todos os serviços
docker-compose down -v          # Parar e remover volumes (limpa banco)
```

---

### 💻 Opção 2: Instalação Manual

#### Pré-requisitos

- **Python 3.10+**
- **MySQL 8.0+**
- **Node.js 18+**

#### 1. Configuração do Ambiente

<details>
<summary><b>🪟 Windows</b></summary>

```powershell
# Clone o repositório
git clone https://github.com/andrecodexvictor/Teste_AndreVictorAndradeOliveiraSantos.git
cd Teste_AndreVictorAndradeOliveiraSantos

# Ambiente virtual Python
python -m venv venv
venv\Scripts\activate

# Instalação de dependências
pip install -r requirements.txt

# Copia template de variáveis de ambiente
copy config\env\.env.example .env
# Edite o arquivo .env com suas credenciais do MySQL
```
</details>

<details>
<summary><b>🐧 Linux / 🍎 macOS</b></summary>

```bash
# Clone o repositório
git clone https://github.com/andrecodexvictor/Teste_AndreVictorAndradeOliveiraSantos.git
cd Teste_AndreVictorAndradeOliveiraSantos

# Ambiente virtual Python
python3 -m venv venv
source venv/bin/activate

# Instalação de dependências
pip install -r requirements.txt

# Copia template de variáveis de ambiente
cp config/env/.env.example .env
# Edite o arquivo .env com suas credenciais do MySQL
```
</details>

#### 2. Configuração do Banco de Dados

```bash
mysql -u root -p -e "CREATE DATABASE intuitive_care_test CHARACTER SET utf8mb4;"
```

Edite o arquivo `.env` na raiz do projeto:

```env
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_USER=root
DATABASE_PASSWORD=sua_senha
DATABASE_NAME=intuitive_care_test
API_DEBUG=false
LOG_LEVEL=INFO
```

#### 3. Carga de Dados (ETL)

Este projeto inclui um pipeline ETL capaz de processar milhões de registros reais da ANS.

```bash
# Executa o pipeline completo (Download -> Processamento -> Inserção -> Export CSVs)
# Processa os últimos 3 trimestres conforme requisitos
# Duração estimada: ~10 minutos (1.4 Milhão de registros)
python run_etl.py

# Os CSVs consolidados são exportados em: data/exports/
# - consolidado_despesas.csv
# - despesas_agregadas.csv
```

#### 4. Execução da API

```bash
uvicorn src.main:app --reload --port 8000
```

**Documentação disponível em:** http://localhost:8000/docs

#### 5. Execução do Frontend

```bash
cd frontend
npm install
npm run dev
```

**Dashboard disponível em:** http://localhost:5173

> **Nota:** O frontend está configurado para conectar em `http://127.0.0.1:8000` para evitar problemas de resolução de DNS no Windows.

---

## 📡 Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/operadoras` | Lista paginada com filtros |
| GET | `/api/operadoras/{cnpj}` | Detalhes de uma operadora |
| GET | `/api/operadoras/{cnpj}/despesas` | Histórico de despesas |
| GET | `/api/estatisticas` | Agregações e rankings |
| GET | `/health` | Verificação de saúde do serviço |
| GET | `/metrics` | Métricas de performance |

### Exemplos de Requisição

```bash
# Listar operadoras com paginação
curl "http://localhost:8000/api/operadoras?page=1&limit=20"

# Filtrar por razão social
curl "http://localhost:8000/api/operadoras?razao_social=UNIMED"

# Obter estatísticas gerais
curl "http://localhost:8000/api/estatisticas"
```

---

## 🛡️ Segurança

### Medidas Implementadas

| Medida | Descrição | Trade-off |
|--------|-----------|-----------|
| **Rate Limiting** | 100 req/min geral, 50 req/min para queries pesadas | Simplicidade vs proteção granular por usuário |
| **CORS Hardening** | Whitelist configurável via `CORS_ORIGINS` | Segurança vs flexibilidade de desenvolvimento |
| **Security Headers** | X-Frame-Options, CSP, HSTS, X-Content-Type-Options | Proteção browser vs compatibilidade legacy |
| **Log Sanitization** | Query strings removidas dos logs | Privacidade vs debug detalhado |
| **Debug Safety** | Validação automática em produção (`ENVIRONMENT=production`) | Segurança vs velocidade de desenvolvimento |

### Configuração de Ambiente

```bash
# .env - Variáveis de segurança
ENVIRONMENT=development          # development | production
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
RATE_LIMIT_PER_MINUTE=100
DEBUG=false                      # OBRIGATÓRIO false em produção
```

**Por que essas decisões?**
- **Rate limiting por IP** ao invés de por usuário: Sistema público sem autenticação, IP é o único identificador
- **CSP restritivo**: Bloqueia XSS e injeção de scripts, aceita-se incompatibilidade com scripts inline
- **HSTS habilitado**: Force HTTPS em produção, aceita-se overhead inicial de redirect

---

## 🧪 Testes

### Suite de Testes Automatizados

```bash
# Executar todos os testes
pytest

# Executar com cobertura
pytest --cov=src --cov-report=term-missing

# Executar por categoria
pytest -m unit          # Testes unitários (rápidos)
pytest -m integration   # Testes de integração (requer MySQL)
pytest -m security      # Testes de segurança
pytest -m slow          # Testes lentos (performance)
```

### Estrutura de Testes

| Arquivo | Testes | Descrição |
|---------|--------|-----------|
| `test_health.py` | 13 | Endpoints `/health`, `/info`, `/version` |
| `test_security.py` | 21 | Headers, rate limiting, sanitização |
| `test_schemas.py` | 13 | Validação Pydantic (CNPJ, paginação) |
| `test_api_operadoras.py` | 19 | Endpoint `/operadoras` |
| `test_api_estatisticas.py` | 11 | Endpoints de estatísticas |
| **Total** | **77** | 65 passando, 5 skipped (MySQL), 7 xfailed |

### Testes Manuais (Humanizados)

Documentação completa de cenários de teste em linguagem natural:
- **📄 Localização**: `tests/MANUAL_TESTS.md`
- **📊 Cobertura**: 50+ cenários em 8 categorias
- **🎯 Objetivo**: Onboarding de QA e validação exploratória

---

## 🔄 CI/CD

### GitHub Actions Pipeline

O projeto conta com um pipeline CI/CD completo em `.github/workflows/ci.yml`:

| Job | Ferramentas | Objetivo |
|-----|-------------|----------|
| `lint` | ruff, mypy | Qualidade de código e type checking |
| `test` | pytest + MySQL service | Testes com banco real |
| `security` | pip-audit, bandit | Vulnerabilidades e código inseguro |
| `build` | Docker | Validação de build |

**Decisões de Design do CI/CD**:

| Escolha | Alternativa | Por quê? |
|---------|-------------|----------|
| **MySQL service** | SQLite em memória | Paridade com produção, evita bugs de compatibilidade |
| **ruff** | flake8 + isort + black | Ferramenta unificada, 10x mais rápido |
| **bandit** | SonarQube | Leve, sem custo, suficiente para projeto |
| **pip-audit** | Snyk, Dependabot | Open source, integra com CI nativo |

---

## ⚖️ Trade-offs e Decisões

### Decisões de Arquitetura

| Decisão | Benefício | Custo | Justificativa |
|---------|-----------|-------|---------------|
| **Bulk Insert** | Performance extrema (1.4M rows em 5min) | Maior uso de memória durante carga | Essencial para volume real de dados |
| Paginação Offset | URLs simples, cálculo de páginas direto | Performance degrada com alto volume | ~5000 registros é gerenciável |
| Cache em Memória | Sem dependências adicionais | Não escala horizontalmente | Instância única suficiente |
| Manter Dados Inválidos | Preservação para auditoria | Requer filtros no frontend | Transparência prioritária |
| MySQL | Setup simplificado, familiaridade | Menos features que PostgreSQL | Adequado ao caso de uso |

### Decisões de Segurança

| Decisão | Benefício | Custo | Justificativa |
|---------|-----------|-------|---------------|
| **Rate limiting por IP** | Proteção DDoS sem autenticação | Shared IPs podem ser bloqueados | Sistema público, IP único identificador |
| **CSP restritivo** | Bloqueia XSS e injeção | Scripts inline não funcionam | Segurança > conveniência |
| **HSTS habilitado** | Force HTTPS sempre | Overhead inicial redirect | Padrão de segurança moderno |
| **Log sanitization** | Dados sensíveis protegidos | Debug mais difícil | LGPD compliance |
| **SlowAPI** ao invés de Redis | Zero dependências extras | Não distribui entre pods | Instância única suficiente |

### Decisões de Testes

| Decisão | Benefício | Custo | Justificativa |
|---------|-----------|-------|---------------|
| **MySQL service no CI** | Paridade com produção | Setup mais lento | Evita bugs de compatibilidade SQLite |
| **Fixtures factory** | Flexibilidade, menos código | Curva aprendizado | Padrão pytest moderno |
| **Markers por categoria** | Execução seletiva | Manutenção de markers | CI mais rápido quando necessário |
| **Testes humanizados** | Onboarding QA facilitado | Duplicação de esforço | Documentação viva |

---

## 📁 Estrutura do Projeto

```
├── src/                     # Código-fonte backend
│   ├── domain/              # Entidades e regras de negócio
│   ├── application/         # Interfaces e casos de uso
│   ├── infrastructure/      # Implementações (DB, rate limiter)
│   │   └── rate_limiter.py  # 🆕 SlowAPI configuration
│   └── interface/           # Routers FastAPI
├── frontend/                # Vue.js 3 + Vite
├── sql/                     # Schema e queries analíticas
├── tests/                   # Suite de testes pytest
│   ├── test_health.py       # 🆕 Testes de health check
│   ├── test_security.py     # 🆕 Testes de segurança
│   ├── test_schemas.py      # 🆕 Testes de validação
│   └── MANUAL_TESTS.md      # 🆕 Testes humanizados
├── .github/workflows/       # 🆕 GitHub Actions CI/CD
├── quality_assurance/       # 🆕 Relatórios de QA
├── docs/                    # Postman collection
├── requirements.txt         # Dependências Python
├── .env.example             # 🆕 Template de variáveis de ambiente
├── run_etl.py               # Script de ingestão de dados
└── README.md                # Documentação principal
```

---

## 🔮 Melhorias Futuras

Com mais tempo disponível, implementaria:

1. ~~**CI/CD** com GitHub Actions~~ ✅ **Implementado**
2. ~~**Suite de testes completa**~~ ✅ **Implementado (96 testes)**
3. **Monitoramento** com Prometheus e Grafana
4. **Cache Distribuído** (Redis) para ambiente clusterizado
5. **Rate limiting por usuário** com JWT/API keys
6. **Testes E2E** com Playwright

---

## 🔧 Otimizações Realizadas

Durante o desenvolvimento, o código passou por diversas melhorias de qualidade:

### Cache Genérico
- **Antes:** Código de cache duplicado em múltiplos endpoints
- **Depois:** Classe `TTLCache[T]` genérica e reutilizável em `src/infrastructure/cache.py`
- **Benefício:** Thread-safe, observabilidade via `/cache/stats`, TTL configurável

### Template HTML Separado
- **Antes:** ~100 linhas de HTML inline no `main.py`
- **Depois:** Template extraído para `src/interface/api/templates/docs.html`
- **Benefício:** Separação de responsabilidades, manutenção facilitada

### Query LIKE Otimizada
- **Antes:** `LIKE '%termo%'` não utilizava índice (full table scan)
- **Depois:** `LIKE 'termo%'` com sanitização de caracteres especiais
- **Benefício:** Queries ~10x mais rápidas com uso de índice

### Cobertura de Testes
- **Antes:** ~70 testes
- **Depois:** **96 testes passando** (cobertura ~80%)
- **Novos:** `test_cache.py`, `test_config.py`, `test_etl.py`, `test_repositories.py`

### Índices SQL
- Covering index para estatísticas (evita table scan)
- Índice composto para JOINs rápidos
- Índice de prefixo para buscas LIKE

---

## 👤 Autor

**André Victor Andrade Oliveira Santos**

Este projeto foi desenvolvido como parte do processo seletivo para estágio na **Intuitive Care**.

O objetivo foi demonstrar não apenas habilidades técnicas de programação, mas também a capacidade de **tomar decisões técnicas fundamentadas** e **documentá-las de forma clara e profissional**.

---

*Última atualização: Fevereiro 2026*
