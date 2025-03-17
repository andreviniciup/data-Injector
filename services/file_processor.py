import os
import zipfile
import tempfile
import logging
from typing import Tuple, Optional

logger = logging.getLogger("FileProcessor")

def extract_zip_file(zip_path: str, extract_to: str = "temp") -> Tuple[Optional[str], Optional[str]]:
    """
    Extrai o conteúdo de um arquivo ZIP e identifica os arquivos de dados e layout.
    
    Args:
        zip_path: Caminho para o arquivo ZIP.
        extract_to: Diretório de extração.
        
    Returns:
        Tuple contendo os caminhos para o arquivo de dados e o arquivo de layout.
    """
    try:
        if not os.path.exists(zip_path):
            logger.error(f"Arquivo ZIP não encontrado: {zip_path}")
            return None, None
        
        # Cria diretório temporário para extração
        os.makedirs(extract_to, exist_ok=True)
        
        # Extrai o arquivo ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        # Lista arquivos extraídos
        extracted_files = os.listdir(extract_to)
        txt_files = [f for f in extracted_files if f.endswith('.txt')]
        
        if len(txt_files) < 2:
            logger.error("Não foram encontrados os dois arquivos TXT esperados.")
            return None, None
        
        # Identifica arquivos de dados e layout
        data_file = None
        layout_file = None
        
        for file in txt_files:
            if "_layout" in file:
                layout_file = os.path.join(extract_to, file)
            else:
                data_file = os.path.join(extract_to, file)
        
        if not data_file or not layout_file:
            logger.error("Não foi possível identificar os arquivos de dados e layout corretamente.")
            return None, None
        
        logger.info(f"Arquivo de dados: {data_file}")
        logger.info(f"Arquivo de layout: {layout_file}")
        
        return data_file, layout_file
    
    except Exception as e:
        logger.error(f"Erro ao extrair o arquivo ZIP: {str(e)}")
        return None, None