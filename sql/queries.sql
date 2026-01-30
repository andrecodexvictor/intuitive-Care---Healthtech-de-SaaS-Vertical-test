-- =============================================================
-- queries.sql - Queries Analíticas Avançadas
-- =============================================================
-- REQUISITOS DO TESTE:
-- 1. Top 5 operadoras com maior crescimento percentual
-- 2. Distribuição de despesas por UF (Top 5 estados)
-- 3. Operadoras acima da média em 2+ trimestres
-- =============================================================

-- =============================================================
-- QUERY 1: Top 5 Operadoras com Maior Crescimento Percentual
-- =============================================================
-- ESTRATÉGIA: Usar window functions para comparar primeiro e último trimestre
-- JUSTIFICATIVA: Crescimento só faz sentido com ambos os pontos de dados
-- =============================================================

WITH trimestres_ordenados AS (
    SELECT 
        d.cnpj,
        o.razao_social,
        d.ano,
        d.trimestre,
        d.valor,
        ROW_NUMBER() OVER (
            PARTITION BY d.cnpj 
            ORDER BY d.ano ASC, d.trimestre ASC
        ) as ordem_asc,
        ROW_NUMBER() OVER (
            PARTITION BY d.cnpj 
            ORDER BY d.ano DESC, d.trimestre DESC
        ) as ordem_desc
    FROM despesas d
    JOIN operadoras o ON d.cnpj = o.cnpj
    WHERE d.valor > 0
),
primeiro_ultimo AS (
    SELECT 
        cnpj,
        razao_social,
        MAX(CASE WHEN ordem_asc = 1 THEN valor END) as valor_primeiro,
        MAX(CASE WHEN ordem_desc = 1 THEN valor END) as valor_ultimo,
        MAX(CASE WHEN ordem_asc = 1 THEN CONCAT(ano, '-Q', trimestre) END) as periodo_primeiro,
        MAX(CASE WHEN ordem_desc = 1 THEN CONCAT(ano, '-Q', trimestre) END) as periodo_ultimo
    FROM trimestres_ordenados
    WHERE ordem_asc = 1 OR ordem_desc = 1
    GROUP BY cnpj, razao_social
    HAVING COUNT(DISTINCT CASE WHEN ordem_asc = 1 OR ordem_desc = 1 THEN 1 END) >= 2
)
SELECT 
    cnpj,
    razao_social,
    valor_primeiro,
    valor_ultimo,
    periodo_primeiro,
    periodo_ultimo,
    ROUND(
        ((valor_ultimo - valor_primeiro) / valor_primeiro) * 100, 
        2
    ) as crescimento_percentual
FROM primeiro_ultimo
WHERE valor_primeiro > 0 AND valor_ultimo > 0
ORDER BY crescimento_percentual DESC
LIMIT 5;


-- =============================================================
-- QUERY 2: Distribuição de Despesas por UF (Top 5 Estados)
-- =============================================================
-- ESTRATÉGIA: JOIN + GROUP BY com SUM e AVG
-- JUSTIFICATIVA: Análise geográfica das despesas
-- =============================================================

SELECT 
    COALESCE(o.uf, 'NÃO INFORMADO') as uf,
    COUNT(DISTINCT o.cnpj) as quantidade_operadoras,
    SUM(d.valor) as total_despesas,
    AVG(d.valor) as media_despesas,
    ROUND(
        SUM(d.valor) / (SELECT SUM(valor) FROM despesas) * 100, 
        2
    ) as percentual_total
FROM operadoras o
JOIN despesas d ON o.cnpj = d.cnpj
GROUP BY o.uf
ORDER BY total_despesas DESC
LIMIT 5;


-- =============================================================
-- QUERY 3: Operadoras com Despesas Acima da Média em 2+ Trimestres
-- =============================================================
-- ESTRATÉGIA: Subquery para média geral + HAVING para filtrar
-- JUSTIFICATIVA: Identificar operadoras consistentemente acima da média
-- =============================================================

WITH media_geral AS (
    SELECT AVG(valor) as media FROM despesas WHERE valor > 0
),
trimestres_acima_media AS (
    SELECT 
        d.cnpj,
        o.razao_social,
        d.ano,
        d.trimestre,
        d.valor,
        mg.media as media_geral,
        CASE WHEN d.valor > mg.media THEN 1 ELSE 0 END as acima_media
    FROM despesas d
    JOIN operadoras o ON d.cnpj = o.cnpj
    CROSS JOIN media_geral mg
    WHERE d.valor > 0
)
SELECT 
    cnpj,
    razao_social,
    COUNT(*) as total_trimestres,
    SUM(acima_media) as trimestres_acima_media,
    ROUND(media_geral, 2) as media_geral_referencia,
    ROUND(AVG(valor), 2) as media_operadora,
    ROUND(SUM(valor), 2) as total_despesas
FROM trimestres_acima_media
GROUP BY cnpj, razao_social, media_geral
HAVING SUM(acima_media) >= 2
ORDER BY total_despesas DESC;


-- =============================================================
-- QUERY BÔNUS: Resumo Estatístico Geral
-- =============================================================

SELECT 
    COUNT(DISTINCT o.cnpj) as total_operadoras,
    COUNT(*) as total_registros_despesas,
    SUM(d.valor) as soma_despesas,
    AVG(d.valor) as media_despesas,
    MIN(d.valor) as menor_despesa,
    MAX(d.valor) as maior_despesa,
    STDDEV(d.valor) as desvio_padrao
FROM operadoras o
JOIN despesas d ON o.cnpj = d.cnpj
WHERE d.valor > 0;
