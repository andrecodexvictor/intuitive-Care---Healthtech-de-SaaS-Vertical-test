# =============================================================
# downloader.py - Download de Arquivos da ANS
# =============================================================
# RESPONSABILIDADE:
# Baixar arquivos de Demonstrações Contábeis da API/FTP da ANS.
#
# URL BASE: https://dadosabertos.ans.gov.br/FTP/PDA/
#
# ESTRUTURA DOS DADOS:
# Os dados estão organizados por ano e trimestre:
# /demonstracoes_contabeis/YYYY/QQ/arquivo.zip
#
# DESAFIOS:
# - Estrutura de diretórios pode variar entre trimestres.
# - Alguns arquivos são CSV, outros XLSX.
# - Tamanho dos arquivos pode ser grande (50-200MB).
#
# ESTRATÉGIA:
# - Usar requests com retry para resiliência.
# - Processar em streaming para não estourar memória.
# - Manter log detalhado de cada etapa.
# =============================================================
import os
import requests
import zipfile
from pathlib import Path
from typing import List, Optional
from loguru import logger
from src.config import settings


# =============================================================
# CONSTANTES
# =============================================================
# URL base do FTP/API da ANS
ANS_BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA"

# Diretório de demonstrações contábeis
DEMONSTRACOES_URL = f"{ANS_BASE_URL}/demonstracoes_contabeis"

# URL do cadastro de operadoras ativas
OPERADORAS_ATIVAS_URL = f"{ANS_BASE_URL}/operadoras_de_plano_de_saude_ativas"

# Timeout para requisições (segundos)
REQUEST_TIMEOUT = 60

# Número de tentativas em caso de falha
MAX_RETRIES = 3


class ANSDownloader:
    """
    Classe para download de dados da ANS.
    
    PADRÃO: Command Pattern
    Cada método executa uma operação específica.
    Permite composição flexível de downloads.
    
    DECISÃO: Classe ao invés de funções soltas.
    JUSTIFICATIVA:
    - Encapsula configuração (data_dir, session).
    - Facilita testes (injetar mock session).
    - Permite reuso de conexão HTTP (session pooling).
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Inicializa o downloader.
        
        Args:
            data_dir: Diretório para salvar arquivos baixados.
                      Se não informado, usa settings.DATA_DIR.
        """
        self.data_dir = Path(data_dir or settings.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Session HTTP reutilizável (connection pooling)
        self.session = requests.Session()
        
        # Headers para simular navegador (alguns servidores bloqueiam requests vazios)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        
        logger.info(f"ANSDownloader inicializado. Data dir: {self.data_dir}")
    
    def _download_file(self, url: str, filename: str) -> Path:
        """
        Baixa um arquivo com retry e progress logging.
        
        STREAMING:
        Usa stream=True para não carregar arquivo inteiro na memória.
        Útil para arquivos grandes (>100MB).
        
        RETRY:
        Tenta até MAX_RETRIES vezes em caso de falha.
        Espera exponencial entre tentativas (1s, 2s, 4s...).
        
        Args:
            url: URL do arquivo para download.
            filename: Nome do arquivo local.
        
        Returns:
            Path do arquivo baixado.
        
        Raises:
            Exception: Se todas as tentativas falharem.
        """
        filepath = self.data_dir / filename
        
        # Se já existe, pula download
        if filepath.exists():
            logger.info(f"Arquivo já existe, pulando: {filename}")
            return filepath
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Baixando: {url} (tentativa {attempt}/{MAX_RETRIES})")
                
                response = self.session.get(
                    url,
                    stream=True,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                
                # Obtém tamanho total se disponível
                total_size = int(response.headers.get("content-length", 0))
                
                # Salva em streaming
                downloaded = 0
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log de progresso a cada 10MB
                        if downloaded % (10 * 1024 * 1024) < 8192:
                            if total_size:
                                percent = downloaded / total_size * 100
                                logger.debug(f"Progresso: {percent:.1f}%")
                
                logger.info(f"Download concluído: {filename} ({downloaded / 1024 / 1024:.1f} MB)")
                return filepath
                
            except requests.RequestException as e:
                logger.warning(f"Erro no download (tentativa {attempt}): {e}")
                
                if attempt == MAX_RETRIES:
                    logger.error(f"Falha após {MAX_RETRIES} tentativas: {url}")
                    raise
                
                # Espera exponencial antes de retry
                import time
                time.sleep(2 ** attempt)
        
        raise RuntimeError(f"Não foi possível baixar: {url}")
    
    def get_ultimos_trimestres(self, quantidade: int = 3) -> List[tuple]:
        """
        Identifica os últimos N trimestres com dados disponíveis.
        
        ESTRATÉGIA:
        Parte do ano/trimestre atual e volta no tempo.
        Verifica se cada trimestre existe na ANS.
        
        DECISÃO: Verificar existência antes de baixar.
        JUSTIFICATIVA:
        - Evita downloads desnecessários.
        - Dados podem não estar disponíveis imediatamente.
        - Logs claros de quais trimestres serão processados.
        
        Args:
            quantidade: Número de trimestres para buscar.
        
        Returns:
            Lista de tuplas (ano, trimestre).
        """
        from datetime import datetime
        
        now = datetime.now()
        year = now.year
        quarter = (now.month - 1) // 3 + 1
        
        trimestres = []
        
        # Busca para trás no tempo
        while len(trimestres) < quantidade and year >= 2020:
            # Verifica se existe (tentativa HEAD request)
            trimestre_url = f"{DEMONSTRACOES_URL}/{year}/{quarter}/"
            
            try:
                resp = self.session.head(trimestre_url, timeout=10)
                if resp.status_code == 200:
                    trimestres.append((year, quarter))
                    logger.info(f"Trimestre encontrado: {year}-Q{quarter}")
            except:
                pass  # Ignora erros, continua buscando
            
            # Move para trimestre anterior
            quarter -= 1
            if quarter < 1:
                quarter = 4
                year -= 1
        
        logger.info(f"Trimestres identificados: {trimestres}")
        return trimestres
    
    def baixar_demonstracoes_contabeis(
        self,
        ano: int,
        trimestre: int,
    ) -> Optional[Path]:
        """
        Baixa arquivo de demonstrações contábeis de um trimestre.
        
        ESTRUTURA DOS ARQUIVOS:
        Os arquivos seguem padrões como:
        - 1T2024.zip
        - 2024_Q1.zip
        - demonstracoes_2024_1.zip
        
        DECISÃO: Tentar múltiplos padrões de nome.
        JUSTIFICATIVA:
        - ANS não tem padrão consistente entre anos.
        - Melhor tentar várias opções que falhar.
        
        Args:
            ano: Ano (YYYY).
            trimestre: Trimestre (1-4).
        
        Returns:
            Path do arquivo baixado ou None se não encontrado.
        """
        # Possíveis padrões de nome de arquivo
        patterns = [
            f"{trimestre}T{ano}.zip",
            f"{ano}_{trimestre}T.zip",
            f"{ano}_Q{trimestre}.zip",
            f"demonstracoes_{ano}_{trimestre}.zip",
            f"{trimestre}t{ano}.zip",
        ]
        
        base_url = f"{DEMONSTRACOES_URL}/{ano}/{trimestre}"
        
        for pattern in patterns:
            url = f"{base_url}/{pattern}"
            
            try:
                # Verifica se arquivo existe (HEAD request)
                resp = self.session.head(url, timeout=10)
                
                if resp.status_code == 200:
                    filename = f"demonstracoes_{ano}_Q{trimestre}.zip"
                    return self._download_file(url, filename)
                    
            except requests.RequestException:
                continue  # Tenta próximo pattern
        
        logger.warning(f"Não encontrado arquivo para {ano}-Q{trimestre}")
        return None
    
    def baixar_operadoras_ativas(self) -> Optional[Path]:
        """
        Baixa cadastro de operadoras ativas.
        
        ARQUIVO:
        Relacao_de_Operadoras.csv (UTF-8)
        Contém: CNPJ, Razão Social, Registro ANS, Modalidade, UF, etc.
        
        ATUALIZAÇÃO:
        Este arquivo é atualizado mensalmente pela ANS.
        """
        # Possíveis nomes de arquivo
        patterns = [
            "Relacao_operadoras.csv",
            "Relacao_de_Operadoras.csv",
            "operadoras_ativas.csv",
        ]
        
        for pattern in patterns:
            url = f"{OPERADORAS_ATIVAS_URL}/{pattern}"
            
            try:
                resp = self.session.head(url, timeout=10)
                
                if resp.status_code == 200:
                    return self._download_file(url, "operadoras_ativas.csv")
                    
            except requests.RequestException:
                continue
        
        logger.error("Não foi possível encontrar arquivo de operadoras ativas")
        return None
    
    def extrair_zip(self, zip_path: Path) -> List[Path]:
        """
        Extrai conteúdo de arquivo ZIP.
        
        DECISÃO: Extrair para subdiretório com nome do ZIP.
        JUSTIFICATIVA:
        - Evita conflito de nomes entre trimestres.
        - Facilita identificar origem do arquivo.
        
        Args:
            zip_path: Caminho do arquivo ZIP.
        
        Returns:
            Lista de caminhos dos arquivos extraídos.
        """
        if not zip_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {zip_path}")
        
        # Diretório de extração
        extract_dir = self.data_dir / zip_path.stem
        extract_dir.mkdir(exist_ok=True)
        
        extracted_files = []
        
        logger.info(f"Extraindo: {zip_path.name}")
        
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                # Pula diretórios
                if member.endswith("/"):
                    continue
                
                # Extrai arquivo
                zf.extract(member, extract_dir)
                extracted_path = extract_dir / member
                extracted_files.append(extracted_path)
                
                logger.debug(f"Extraído: {member}")
        
        logger.info(f"Extração concluída: {len(extracted_files)} arquivos")
        return extracted_files
