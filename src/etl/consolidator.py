# =============================================================
# consolidator.py - Consolidação e Export de Dados
# =============================================================
# RESPONSABILIDADE:
# 1. Combinar dados de múltiplos trimestres.
# 2. Enriquecer com dados cadastrais das operadoras.
# 3. Calcular agregações (total, média, desvio padrão).
# 4. Exportar CSVs finais.
#
# OUTPUT:
# - consolidado_despesas.csv: Dados individuais consolidados
# - despesas_agregadas.csv: Dados agregados por operadora/UF
# =============================================================
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Optional
from loguru import logger
from src.config import settings


class DataConsolidator:
    """
    Consolidador de dados de múltiplos trimestres.
    
    FLUXO:
    1. Recebe DataFrames de cada trimestre.
    2. Concatena em um único DataFrame.
    3. Enriquece com cadastro de operadoras.
    4. Calcula agregações.
    5. Exporta CSVs.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Inicializa o consolidador.
        
        Args:
            output_dir: Diretório para salvar arquivos.
        """
        self.output_dir = Path(output_dir or settings.DATA_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.df_consolidado: Optional[pd.DataFrame] = None
        self.df_operadoras: Optional[pd.DataFrame] = None
    
    def consolidar_trimestres(
        self,
        dataframes: List[pd.DataFrame],
        anos: List[int],
        trimestres: List[int],
    ) -> pd.DataFrame:
        """
        Consolida múltiplos DataFrames em um único.
        
        TRATAMENTO DE DUPLICADOS:
        DECISÃO: Manter registro mais recente para mesmo CNPJ+período.
        JUSTIFICATIVA:
        - Dados corrigidos são geralmente publicados depois.
        - Evita contagem duplicada.
        - Flag "DUPLICADO" marca que havia duplicatas.
        
        Args:
            dataframes: Lista de DataFrames (um por trimestre).
            anos: Lista de anos correspondentes.
            trimestres: Lista de trimestres correspondentes.
        
        Returns:
            DataFrame consolidado.
        """
        if len(dataframes) != len(anos) or len(dataframes) != len(trimestres):
            raise ValueError("Listas devem ter mesmo tamanho")
        
        # Adiciona ano/trimestre a cada DataFrame
        enhanced_dfs = []
        for df, ano, tri in zip(dataframes, anos, trimestres):
            df = df.copy()
            
            # Se não tem coluna ANO/TRIMESTRE, adiciona
            if "ANO" not in df.columns:
                df["ANO"] = ano
            if "TRIMESTRE" not in df.columns:
                df["TRIMESTRE"] = tri
            
            enhanced_dfs.append(df)
        
        # Concatena todos
        logger.info(f"Consolidando {len(enhanced_dfs)} trimestres...")
        df_all = pd.concat(enhanced_dfs, ignore_index=True)
        
        total_original = len(df_all)
        
        # Identifica duplicados (mesmo CNPJ, ANO, TRIMESTRE)
        duplicates_mask = df_all.duplicated(
            subset=["CNPJ", "ANO", "TRIMESTRE"],
            keep="last",  # Mantém mais recente
        )
        
        num_duplicates = duplicates_mask.sum()
        
        if num_duplicates > 0:
            logger.warning(f"Encontrados {num_duplicates} registros duplicados")
            
            # Marca duplicados antes de remover
            df_all.loc[duplicates_mask, "STATUS_QUALIDADE"] = "DUPLICADO"
            
            # Remove duplicados, mantém último
            df_all = df_all.drop_duplicates(
                subset=["CNPJ", "ANO", "TRIMESTRE"],
                keep="last",
            )
            
            logger.info(f"Após remoção: {len(df_all)} registros (de {total_original})")
        
        self.df_consolidado = df_all
        return df_all
    
    def carregar_operadoras(self, filepath: Path) -> pd.DataFrame:
        """
        Carrega cadastro de operadoras ativas.
        
        NORMALIZAÇÃO:
        - CNPJ: Remove formatação.
        - Colunas: Normaliza nomes.
        """
        logger.info(f"Carregando cadastro de operadoras: {filepath}")
        
        df = pd.read_csv(filepath, encoding="utf-8", sep=";")
        
        # Mapeia colunas para nomes padrão
        column_map = {}
        
        # Busca CNPJ
        for col in df.columns:
            col_upper = col.upper()
            if "CNPJ" in col_upper:
                column_map[col] = "CNPJ"
            elif "RAZAO" in col_upper or "RAZÃO" in col_upper:
                column_map[col] = "RAZAO_SOCIAL_CADASTRO"
            elif "REGISTRO" in col_upper and "ANS" in col_upper:
                column_map[col] = "REGISTRO_ANS"
            elif "MODALIDADE" in col_upper:
                column_map[col] = "MODALIDADE"
            elif col_upper == "UF" or "ESTADO" in col_upper:
                column_map[col] = "UF"
        
        df = df.rename(columns=column_map)
        
        # Limpa CNPJ
        if "CNPJ" in df.columns:
            df["CNPJ"] = df["CNPJ"].astype(str).str.replace(r"\D", "", regex=True)
            df["CNPJ"] = df["CNPJ"].str.zfill(14)
        
        logger.info(f"Operadoras carregadas: {len(df)}")
        self.df_operadoras = df
        return df
    
    def enriquecer_com_cadastro(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriquece dados com informações cadastrais.
        
        JOIN:
        DECISÃO: Left join (manter todos os registros de despesas).
        JUSTIFICATIVA:
        - Não perder despesas de operadoras não encontradas.
        - Marcar como SEM_CADASTRO para análise.
        
        TRATAMENTO DE NO-MATCH:
        - Operadora não encontrada: STATUS = SEM_CADASTRO
        - Múltiplos matches: Usa primeiro (ordenado por registro ANS)
        """
        if self.df_operadoras is None:
            logger.warning("Cadastro de operadoras não carregado. Pulando enriquecimento.")
            return df
        
        logger.info("Enriquecendo dados com cadastro...")
        
        # Remove duplicatas do cadastro (pode ter CNPJs repetidos)
        operadoras_unique = self.df_operadoras.drop_duplicates(
            subset=["CNPJ"],
            keep="first",
        )
        
        # Prepara colunas para join
        cols_to_add = ["CNPJ", "REGISTRO_ANS", "MODALIDADE", "UF"]
        cols_available = [c for c in cols_to_add if c in operadoras_unique.columns]
        
        # Left join
        df_enriched = df.merge(
            operadoras_unique[cols_available],
            on="CNPJ",
            how="left",
            indicator=True,
        )
        
        # Marca registros sem match
        no_match_mask = df_enriched["_merge"] == "left_only"
        no_match_count = no_match_mask.sum()
        
        if no_match_count > 0:
            logger.warning(f"Registros sem match no cadastro: {no_match_count}")
            
            # Marca status (não sobrescreve outros problemas)
            ok_mask = df_enriched["STATUS_QUALIDADE"] == "OK"
            df_enriched.loc[no_match_mask & ok_mask, "STATUS_QUALIDADE"] = "SEM_CADASTRO"
        
        # Remove coluna indicadora
        df_enriched = df_enriched.drop(columns=["_merge"])
        
        logger.info(f"Enriquecimento concluído. Registros: {len(df_enriched)}")
        return df_enriched
    
    def calcular_agregacoes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula agregações por Razão Social + UF.
        
        MÉTRICAS:
        - total: SUM(valor)
        - media: AVG(valor) por trimestre
        - desvio_padrao: STD(valor) - variabilidade
        - quantidade_registros: COUNT(*)
        
        ORDENAÇÃO: Por total (maior primeiro).
        """
        logger.info("Calculando agregações...")
        
        # Garante que RAZAO_SOCIAL existe
        if "RAZAO_SOCIAL" not in df.columns:
            if "RAZAO_SOCIAL_CADASTRO" in df.columns:
                df["RAZAO_SOCIAL"] = df["RAZAO_SOCIAL_CADASTRO"]
            else:
                df["RAZAO_SOCIAL"] = df["CNPJ"]  # Fallback
        
        # Preenche UF vazio
        if "UF" not in df.columns:
            df["UF"] = "N/A"
        else:
            df["UF"] = df["UF"].fillna("N/A")
        
        # Agrupa por Razão Social + UF
        df_agg = df.groupby(["RAZAO_SOCIAL", "UF"], as_index=False).agg(
            total=("VALOR", "sum"),
            media=("VALOR", "mean"),
            desvio_padrao=("VALOR", "std"),
            quantidade_registros=("VALOR", "count"),
        )
        
        # Preenche NaN do desvio padrão (quando só tem 1 registro)
        df_agg["desvio_padrao"] = df_agg["desvio_padrao"].fillna(0)
        
        # Ordena por total (maior primeiro)
        df_agg = df_agg.sort_values("total", ascending=False)
        
        logger.info(f"Agregações calculadas: {len(df_agg)} grupos")
        return df_agg
    
    def exportar_csv(
        self,
        df: pd.DataFrame,
        filename: str,
        compress: bool = True,
    ) -> Path:
        """
        Exporta DataFrame para CSV.
        
        ENCODING: UTF-8 (padrão brasileiro).
        SEPARADOR: ; (mais comum em dados brasileiros).
        COMPRESSÃO: ZIP opcional.
        """
        filepath = self.output_dir / filename
        
        logger.info(f"Exportando: {filename} ({len(df)} registros)")
        
        # Salva CSV
        df.to_csv(
            filepath,
            sep=";",
            index=False,
            encoding="utf-8-sig",  # Com BOM para Excel brasileiro
        )
        
        if compress:
            import zipfile
            
            zip_path = filepath.with_suffix(".zip")
            
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(filepath, filepath.name)
            
            # Remove CSV original
            filepath.unlink()
            
            logger.info(f"Compactado: {zip_path.name}")
            return zip_path
        
        return filepath
    
    def executar_pipeline_completo(
        self,
        arquivos_despesas: List[Path],
        arquivo_operadoras: Optional[Path],
        anos: List[int],
        trimestres: List[int],
    ) -> dict:
        """
        Executa pipeline completo de consolidação.
        
        ETAPAS:
        1. Lê cada arquivo de despesas.
        2. Processa e valida.
        3. Consolida trimestres.
        4. Enriquece com cadastro.
        5. Calcula agregações.
        6. Exporta CSVs.
        
        Returns:
            Dict com caminhos dos arquivos gerados e estatísticas.
        """
        from src.etl.processor import DataProcessor
        
        processor = DataProcessor()
        dataframes = []
        
        # 1. Lê e processa cada arquivo
        for filepath in arquivos_despesas:
            df = processor.read_file(filepath)
            df = processor.normalize_columns(df)
            df = processor.validate_dataframe(df)
            df = processor.filter_despesas(df)
            dataframes.append(df)
        
        # 2. Consolida trimestres
        df_consolidado = self.consolidar_trimestres(dataframes, anos, trimestres)
        
        # 3. Carrega e enriquece com cadastro
        if arquivo_operadoras and arquivo_operadoras.exists():
            self.carregar_operadoras(arquivo_operadoras)
            df_consolidado = self.enriquecer_com_cadastro(df_consolidado)
        
        # 4. Calcula agregações
        df_agregado = self.calcular_agregacoes(df_consolidado)
        
        # 5. Exporta CSVs
        path_consolidado = self.exportar_csv(
            df_consolidado,
            "consolidado_despesas.csv",
            compress=True,
        )
        
        path_agregado = self.exportar_csv(
            df_agregado,
            "despesas_agregadas.csv",
            compress=False,
        )
        
        # Estatísticas finais
        stats = {
            "total_registros": len(df_consolidado),
            "total_grupos": len(df_agregado),
            "cnpjs_unicos": df_consolidado["CNPJ"].nunique(),
            "ufs": df_consolidado["UF"].nunique() if "UF" in df_consolidado.columns else 0,
            "arquivo_consolidado": str(path_consolidado),
            "arquivo_agregado": str(path_agregado),
        }
        
        logger.info("Pipeline concluído com sucesso!")
        logger.info(f"Estatísticas: {stats}")
        
        return stats
