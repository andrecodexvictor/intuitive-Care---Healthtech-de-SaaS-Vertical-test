-- =============================================================
-- schema.sql - Script de Criação do Banco de Dados (MySQL 8.0)
-- =============================================================
-- INSTRUÇÕES DE EXECUÇÃO:
-- 1. Conecte ao MySQL: mysql -u root -p
-- 2. Execute este script: source schema.sql
--
-- OU via linha de comando:
-- mysql -u root -p < schema.sql
--
-- NOTA: Este script é para referência/documentação.
-- As tabelas são criadas automaticamente pelo SQLAlchemy.
-- =============================================================

-- Cria o banco de dados
CREATE DATABASE IF NOT EXISTS intuitive_care_test
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE intuitive_care_test;

-- =============================================================
-- TABELA: operadoras
-- =============================================================
-- Armazena dados cadastrais das operadoras de plano de saúde.
-- CHAVE PRIMÁRIA: CNPJ (único por definição).
-- =============================================================
CREATE TABLE IF NOT EXISTS operadoras (
    cnpj VARCHAR(14) NOT NULL PRIMARY KEY,  -- CNPJ sem formatação
    razao_social VARCHAR(200) NOT NULL,      -- Nome oficial
    registro_ans VARCHAR(6),                 -- Código ANS (opcional)
    modalidade VARCHAR(50),                  -- Tipo: Cooperativa, Seguradora, etc.
    uf CHAR(2),                              -- UF da sede
    
    -- ÍNDICES para queries frequentes
    INDEX idx_razao_social (razao_social),
    INDEX idx_uf (uf)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================
-- TABELA: despesas
-- =============================================================
-- Registros individuais de despesas por operadora/trimestre.
-- 
-- DECISÃO: ID auto-incremento ao invés de chave composta.
-- JUSTIFICATIVA: Pode haver múltiplas despesas da mesma operadora
-- no mesmo trimestre (diferentes categorias de despesa).
-- =============================================================
CREATE TABLE IF NOT EXISTS despesas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cnpj VARCHAR(14) NOT NULL,               -- FK para operadoras
    razao_social VARCHAR(200),               -- Desnormalizado para export
    ano SMALLINT NOT NULL,                   -- Ano (YYYY)
    trimestre TINYINT NOT NULL,              -- Trimestre (1-4)
    valor DECIMAL(15, 2) NOT NULL,           -- Valor em R$
    status_qualidade VARCHAR(20) DEFAULT 'OK',  -- Flag de qualidade
    
    -- FOREIGN KEY para integridade referencial
    FOREIGN KEY (cnpj) REFERENCES operadoras(cnpj)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    
    -- ÍNDICES para queries analíticas
    INDEX idx_periodo (ano, trimestre),
    INDEX idx_cnpj_periodo (cnpj, ano, trimestre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================
-- TABELA: despesas_agregadas
-- =============================================================
-- Dados pré-calculados de agregação por operadora/UF.
-- ATUALIZAÇÃO: Recalculada após cada ingestão de dados.
-- =============================================================
CREATE TABLE IF NOT EXISTS despesas_agregadas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    razao_social VARCHAR(200) NOT NULL,
    uf CHAR(2),
    total DECIMAL(18, 2) NOT NULL,           -- SUM(despesas)
    media DECIMAL(15, 2) NOT NULL,           -- AVG(despesas)
    desvio_padrao DECIMAL(15, 2) DEFAULT 0,  -- STD(despesas)
    quantidade_registros INT DEFAULT 0,      -- COUNT(*)
    
    INDEX idx_razao_social (razao_social),
    INDEX idx_uf (uf),
    INDEX idx_total (total)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =============================================================
-- COMENTÁRIOS DAS TABELAS (para documentação no banco)
-- =============================================================
ALTER TABLE operadoras COMMENT = 'Cadastro de operadoras de planos de saúde registradas na ANS';
ALTER TABLE despesas COMMENT = 'Registros individuais de despesas contábeis por trimestre';
ALTER TABLE despesas_agregadas COMMENT = 'Dados agregados pré-calculados para performance da API';
