import os
import shutil
import tempfile
from typing import Optional, Tuple

def create_temp_dir() -> str:
    """
    Cria um diretório temporário.
    
    Returns:
        Caminho do diretório temporário.
    """
    return tempfile.mkdtemp()

def remove_temp_dir(temp_dir: str):
    """
    Remove um diretório temporário e seu conteúdo.
    
    Args:
        temp_dir: Caminho do diretório temporário.
    """
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

def get_file_name(file_path: str) -> str:
    """
    Extrai o nome do arquivo sem a extensão.
    
    Args:
        file_path: Caminho do arquivo.
        
    Returns:
        Nome do arquivo sem extensão.
    """
    return os.path.splitext(os.path.basename(file_path))[0]

def is_valid_zip(file_path: str) -> bool:
    """
    Verifica se o arquivo é um ZIP válido.
    
    Args:
        file_path: Caminho do arquivo.
        
    Returns:
        True se for um ZIP válido, False caso contrário.
    """
    return file_path.endswith('.zip') and os.path.exists(file_path)