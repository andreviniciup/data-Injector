import os
import zipfile 
import tempfile
import logging
from typing import Tuple, Optional, List, Dict, Any
from app.utils.file_utils import create_temp_dir, remove_temp_dir, is_valid_zip, get_file_name
from app.services.data_validator import (
    parse_layout_file, 
    validate_database_schema, 
    validate_fixed_width_data,
    parse_fixed_width_data
)
from app.services.database_service import insert_records_safely

logger = logging.getLogger("FileProcessor")

def extract_zip_file(zip_path: str, extract_to: str = "temp") -> Tuple[Optional[str], Optional[str]]:
    """
    Extrai o conteúdo de um arquivo ZIP e identifica os arquivos de dados e layout.
    """
    temp_dir = None
    try:
        if not is_valid_zip(zip_path):
            logger.error(f"Arquivo ZIP inválido ou não encontrado: {zip_path}")
            return None, None
        
        # Cria diretório temporário para extração
        temp_dir = create_temp_dir()
        
        # Extrai o arquivo ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Lista arquivos extraídos
        extracted_files = os.listdir(temp_dir)
        txt_files = [f for f in extracted_files if f.endswith('.txt')]
        
        if len(txt_files) < 2:
            logger.error("Não foram encontrados os dois arquivos TXT esperados.")
            remove_temp_dir(temp_dir)
            return None, None
        
        # Identifica arquivos de dados e layout
        data_file = None
        layout_file = None
        
        for file in txt_files:
            if "_layout" in file:
                layout_file = os.path.join(temp_dir, file)
            else:
                data_file = os.path.join(temp_dir, file)
        
        if not data_file or not layout_file:
            logger.error("Não foi possível identificar os arquivos de dados e layout corretamente.")
            remove_temp_dir(temp_dir)
            return None, None
        
        logger.info(f"Arquivo de dados: {data_file}")
        logger.info(f"Arquivo de layout: {layout_file}")
        
        return data_file, layout_file
    
    except Exception as e:
        logger.error(f"Erro ao extrair o arquivo ZIP: {str(e)}")
        if temp_dir:
            remove_temp_dir(temp_dir)
        return None, None

def process_file_upload(zip_path: str) -> Dict[str, Any]:
    """
    Processa o upload de um arquivo ZIP, realizando validações e inserção no banco.
    
    Args:
        zip_path: Caminho do arquivo ZIP
        
    Returns:
        Dicionário com resultado do processamento
    """
    try:
        # Extrai arquivos do ZIP
        data_file, layout_file = extract_zip_file(zip_path)
        
        if not data_file or not layout_file:
            return {
                "success": False, 
                "message": "Falha ao extrair arquivos do ZIP"
            }
        
        # Lê layout
        layout_columns = parse_layout_file(layout_file)
        if not layout_columns:
            return {
                "success": False, 
                "message": "Falha ao interpretar arquivo de layout"
            }
        
        # Identifica nome da tabela
        table_name = get_file_name(data_file).replace('_layout', '')
        
        # Valida schema do banco de dados
        if not validate_database_schema(table_name, layout_columns):
            return {
                "success": False, 
                "message": "Estrutura da tabela incompatível com o layout"
            }
        
        # Valida dados de largura fixa
        if not validate_fixed_width_data(data_file, layout_columns):
            return {
                "success": False, 
                "message": "Dados inválidos no arquivo"
            }
        
        # Converte dados para lista de registros
        records = parse_fixed_width_data(data_file, layout_columns)
        
        # Insere registros no banco
        success = insert_records_safely(table_name, records)
        
        return {
            "success": success, 
            "message": "Processamento concluído com sucesso" if success else "Falha ao inserir registros"
        }
    
    except Exception as e:
        logger.error(f"Erro durante o processamento: {str(e)}")
        return {
            "success": False, 
            "message": f"Erro inesperado: {str(e)}"
        }