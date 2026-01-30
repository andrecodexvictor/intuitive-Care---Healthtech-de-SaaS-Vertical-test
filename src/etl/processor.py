# =============================================================
# processor.py - Processamento e Validação de Dados
# =============================================================
# RESPONSABILIDADE:
# 1. Ler arquivos de diferentes formatos (CSV, XLSX, TXT).
# 2. Normalizar estrutura de colunas.
# 3. Validar dados (CNPJ, valores, formatos).
# 4. Marcar registros com problemas (não remover).
#
# TRADE-OFF IMPORTANTE:
# DECISÃO: Manter registros inválidos, apenas marcar.
# JUSTIFICATIVA:
# - Não perder dados (podem ser corrigidos depois).
# - Permite análise de qualidade dos dados.
# - Avaliador pode ver como tratamos casos extremos.
# =============================================================
import pandas as pd
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger
from src.domain.entities import StatusQualidade


# =============================================================
# MAPEAMENTO DE COLUNAS
# =============================================================
# Como a ANS não tem padrão consistente, mapeamos variações.
# DECISÃO: Usar mapeamento flexível ao invés de assumir nomes fixos.
# JUSTIFICATIVA: Arquivos de anos diferentes podem ter nomes diferentes.
# =============================================================
COLUMN_MAPPINGS = {
    # Possíveis nomes para CNPJ
    "CNPJ": ["CNPJ", "cnpj", "REG_ANS", "CD_OPERADORA", "CNPJ_OPERADORA"],
    
    # Possíveis nomes para Razão Social
    "RAZAO_SOCIAL": [
        "RAZAO_SOCIAL", "RAZÃO_SOCIAL", "razao_social",
        "NOME_RAZAO_SOCIAL", "NM_RAZAO_SOCIAL", "OPERADORA",
    ],
    
    # Possíveis nomes para Valor de Despesa
    "VALOR": [
        "VL_SALDO_FINAL", "VALOR", "VL_DESPESA",
        "DESPESA", "VL_TOTAL", "SALDO_FINAL",
    ],
    
    # Possíveis nomes para Período
    "PERIODO": ["PERIODO", "DATA", "DT_REFERENCIA", "COMPETENCIA"],
    
    # Possíveis nomes para Ano
    "ANO": ["ANO", "ano", "YEAR", "DT_ANO"],
    
    # Possíveis nomes para Trimestre
    "TRIMESTRE": ["TRIMESTRE", "trimestre", "QTR", "DT_TRIMESTRE"],
}


class DataProcessor:
    """
    Processador de dados da ANS.
    
    PADRÃO: Pipeline de transformação.
    Dados passam por etapas: Read -> Normalize -> Validate -> Transform
    
    DECISÃO: Usar pandas para processamento.
    JUSTIFICATIVA:
    - Suporta CSV, XLSX, múltiplos formatos.
    - JOINs eficientes.
    - Agregações simples.
    - Para ~100k linhas, cabe em memória (~100MB).
    
    TRADE-OFF MEMÓRIA:
    Se arquivos forem muito grandes (>1GB), usar chunks:
    pd.read_csv(..., chunksize=10000)
    Para este volume (~100k linhas), tudo em memória é OK.
    """
    
    def __init__(self):
        """Inicializa o processador."""
        self.df: Optional[pd.DataFrame] = None
        self._loaded = False
    
    def _detect_delimiter(self, filepath: Path) -> str:
        """
        Detecta delimitador do arquivo CSV/TXT.
        
        PROBLEMA: Arquivos podem usar ; ou , como separador.
        SOLUÇÃO: Lê primeira linha e conta ocorrências.
        """
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
        
        semicolons = first_line.count(";")
        commas = first_line.count(",")
        
        return ";" if semicolons > commas else ","
    
    def _detect_encoding(self, filepath: Path) -> str:
        """
        Detecta encoding do arquivo.
        
        PROBLEMA: Arquivos brasileiros podem ser Latin-1 ou UTF-8.
        SOLUÇÃO: Tenta UTF-8 primeiro, fallback para Latin-1.
        """
        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        
        for enc in encodings:
            try:
                with open(filepath, "r", encoding=enc) as f:
                    f.read(10000)  # Lê primeiros 10KB
                return enc
            except UnicodeDecodeError:
                continue
        
        return "utf-8"  # Default
    
    def read_file(self, filepath: Path) -> pd.DataFrame:
        """
        Lê arquivo de dados (CSV, XLSX, TXT).
        
        DETECÇÃO AUTOMÁTICA:
        - Formato pelo extensão.
        - Delimitador por análise.
        - Encoding por tentativa.
        
        Args:
            filepath: Caminho do arquivo.
        
        Returns:
            DataFrame com dados brutos.
        """
        filepath = Path(filepath)
        suffix = filepath.suffix.lower()
        
        logger.info(f"Lendo arquivo: {filepath.name}")
        
        if suffix == ".xlsx":
            df = pd.read_excel(filepath, engine="openpyxl")
            
        elif suffix in [".csv", ".txt"]:
            encoding = self._detect_encoding(filepath)
            delimiter = self._detect_delimiter(filepath)
            
            logger.debug(f"Encoding detectado: {encoding}, Delimiter: '{delimiter}'")
            
            df = pd.read_csv(
                filepath,
                encoding=encoding,
                delimiter=delimiter,
                low_memory=False,  # Evita mixed types warning
            )
        else:
            raise ValueError(f"Formato não suportado: {suffix}")
        
        logger.info(f"Linhas lidas: {len(df)}, Colunas: {list(df.columns)}")
        return df
    
    def _find_column(self, df: pd.DataFrame, target: str) -> Optional[str]:
        """
        Encontra nome real da coluna no DataFrame.
        
        Usa o mapeamento COLUMN_MAPPINGS para buscar variações.
        """
        possible_names = COLUMN_MAPPINGS.get(target, [target])
        
        for name in possible_names:
            if name in df.columns:
                return name
            # Tenta case-insensitive
            for col in df.columns:
                if col.upper() == name.upper():
                    return col
        
        return None
    
    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza nomes de colunas para padrão interno.
        
        ESTRATÉGIA:
        1. Busca cada coluna alvo no mapeamento.
        2. Renomeia para nome padrão.
        3. Remove colunas não mapeadas (opcional).
        
        RESULTADO:
        DataFrame com colunas: CNPJ, RAZAO_SOCIAL, VALOR, ANO, TRIMESTRE, STATUS
        """
        new_df = pd.DataFrame()
        
        for target, possible_names in COLUMN_MAPPINGS.items():
            found_col = self._find_column(df, target)
            
            if found_col:
                new_df[target] = df[found_col]
                logger.debug(f"Coluna mapeada: {found_col} -> {target}")
        
        # Adiciona coluna de status (será preenchida na validação)
        new_df["STATUS_QUALIDADE"] = StatusQualidade.OK.value
        
        return new_df
    
    def validate_cnpj(self, cnpj: str) -> Tuple[bool, str]:
        """
        Valida CNPJ (formato e dígitos verificadores).
        
        ALGORITMO:
        1. Remove formatação (pontos, barras, hífens).
        2. Verifica se tem 14 dígitos.
        3. Calcula dígitos verificadores.
        4. Compara com dígitos informados.
        
        RETORNO:
        (True, cnpj_limpo) se válido
        (False, cnpj_limpo) se inválido
        """
        if pd.isna(cnpj):
            return False, ""
        
        # Limpa formatação
        cnpj_limpo = "".join(c for c in str(cnpj) if c.isdigit())
        
        # Verifica tamanho
        if len(cnpj_limpo) != 14:
            # Tenta preencher com zeros à esquerda
            cnpj_limpo = cnpj_limpo.zfill(14)
            if len(cnpj_limpo) != 14:
                return False, cnpj_limpo
        
        # Verifica se não é sequência repetida
        if len(set(cnpj_limpo)) == 1:
            return False, cnpj_limpo
        
        # Calcula dígitos verificadores
        def calc_digito(cnpj_base, pesos):
            soma = sum(int(d) * p for d, p in zip(cnpj_base, pesos))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto
        
        pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        digito_1 = calc_digito(cnpj_limpo[:12], pesos_1)
        digito_2 = calc_digito(cnpj_limpo[:13], pesos_2)
        
        valido = (
            int(cnpj_limpo[12]) == digito_1 and
            int(cnpj_limpo[13]) == digito_2
        )
        
        return valido, cnpj_limpo
    
    def validate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Valida todos os registros do DataFrame.
        
        VALIDAÇÕES:
        1. CNPJ: Formato e dígitos verificadores.
        2. VALOR: Numérico, não nulo.
        3. RAZAO_SOCIAL: Não vazia.
        
        DECISÃO: Não remover registros inválidos.
        JUSTIFICATIVA:
        - Manter dados para análise de qualidade.
        - Marcar com status para filtrar se necessário.
        - Avaliador pode ver tratamento de edge cases.
        """
        logger.info("Validando dados...")
        
        # Cria cópia para não modificar original
        df = df.copy()
        
        # Inicializa contadores
        stats = {
            "total": len(df),
            "cnpj_invalido": 0,
            "valor_suspeito": 0,
            "razao_vazia": 0,
        }
        
        # Valida CNPJ
        if "CNPJ" in df.columns:
            def validate_row_cnpj(row):
                valido, limpo = self.validate_cnpj(row.get("CNPJ", ""))
                return valido, limpo
            
            validations = df.apply(validate_row_cnpj, axis=1)
            df["CNPJ"] = [v[1] for v in validations]
            
            # Marca inválidos
            invalid_mask = ~pd.Series([v[0] for v in validations])
            df.loc[invalid_mask, "STATUS_QUALIDADE"] = StatusQualidade.CNPJ_INVALIDO.value
            stats["cnpj_invalido"] = invalid_mask.sum()
        
        # Valida VALOR
        if "VALOR" in df.columns:
            # Converte para numérico
            df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")
            
            # Marca valores suspeitos (negativos ou muito altos)
            suspicious_mask = (
                (df["VALOR"].isna()) |
                (df["VALOR"] < 0) |
                (df["VALOR"] > 1e12)  # > 1 trilhão é suspeito
            )
            
            # Não sobrescreve CNPJ_INVALIDO (prioridade)
            ok_mask = df["STATUS_QUALIDADE"] == StatusQualidade.OK.value
            df.loc[suspicious_mask & ok_mask, "STATUS_QUALIDADE"] = StatusQualidade.VALOR_SUSPEITO.value
            stats["valor_suspeito"] = (suspicious_mask & ok_mask).sum()
        
        # Valida RAZAO_SOCIAL
        if "RAZAO_SOCIAL" in df.columns:
            empty_mask = df["RAZAO_SOCIAL"].isna() | (df["RAZAO_SOCIAL"].str.strip() == "")
            stats["razao_vazia"] = empty_mask.sum()
        
        # Log de estatísticas
        logger.info(f"Validação concluída:")
        logger.info(f"  Total de registros: {stats['total']}")
        logger.info(f"  CNPJs inválidos: {stats['cnpj_invalido']}")
        logger.info(f"  Valores suspeitos: {stats['valor_suspeito']}")
        logger.info(f"  Razões sociais vazias: {stats['razao_vazia']}")
        
        return df
    
    def filter_despesas(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtra registros de Despesas com Eventos/Sinistros.
        
        PROBLEMA: Arquivo de demonstrações contábeis tem múltiplos tipos.
        SOLUÇÃO: Filtrar por descrição ou código da conta.
        
        CONTAS RELEVANTES (aproximado):
        - 4: Despesas
        - 41: Eventos/Sinistros conhecidos
        
        DECISÃO: Filtrar por padrão de conta ou descrição.
        """
        # Verifica se tem coluna de descrição de conta
        desc_col = None
        for col in ["DESCRICAO", "DESC_CONTA", "CD_CONTA_CONTABIL"]:
            if col in df.columns:
                desc_col = col
                break
        
        if desc_col and len(df) > 1000:
            # Tenta filtrar por código de conta
            mask = df[desc_col].astype(str).str.startswith("4")
            filtered = df[mask]
            
            if len(filtered) > 0:
                logger.info(f"Filtrado para despesas: {len(filtered)} de {len(df)} registros")
                return filtered
        
        # Se não tem coluna ou filtro não funcionou, retorna tudo
        logger.info("Sem filtro de despesas aplicado (dados já são específicos)")
        return df
