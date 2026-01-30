# =============================================================
# etl/__init__.py - Módulo de ETL (Extract, Transform, Load)
# =============================================================
# Este módulo implementa o "Agente de Ingestão e Normalização" (AIN).
#
# RESPONSABILIDADES:
# 1. Download de dados da ANS (API/FTP público).
# 2. Extração de arquivos ZIP.
# 3. Normalização de formatos (CSV, XLSX, TXT).
# 4. Validação de dados (CNPJ, valores).
# 5. Enriquecimento (join com cadastro de operadoras).
# 6. Persistência no banco de dados.
#
# PADRÃO: Pipeline Pattern
# Dados fluem por etapas: Download -> Extract -> Normalize -> Validate -> Load
# =============================================================
