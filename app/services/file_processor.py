import os
import zipfile 
import tempfile
import logging
import asyncio
from typing import Tuple, Optional, List, Dict, Any
from sqlalchemy import text
from app.models.database import SessionLocal
from app.utils.file_utils import create_temp_dir, remove_temp_dir, is_valid_zip, get_file_name
from app.services.data_validator import (
    parse_layout_file, 
    validate_database_schema, 
    validate_fixed_width_data,
    parse_fixed_width_data
)
from app.services.database_service import insert_records_safely
from config import DATABASE_SCHEMA
from app.services.data_sync_service import sync_data_for_matched_tables

logger = logging.getLogger("FileProcessor")

def get_database_tables() -> List[str]:
    """
    Recupera a lista de tabelas do banco de dados.
    
    Returns:
        Lista de nomes de tabelas no esquema configurado.
    """
    try:
        with SessionLocal() as session:
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema
            """)
            
            result = session.execute(query, {'schema': DATABASE_SCHEMA})
            tables = [row.table_name for row in result]
        
        logger.info(f"Tabelas encontradas no banco de dados: {tables}")
        return tables
    
    except Exception as e:
        logger.error(f"Erro ao recuperar tabelas do banco de dados: {str(e)}")
        return []

def match_files_to_tables(extracted_files: List[str], database_tables: List[str]) -> Dict[str, Optional[str]]:
    """
    Encontra correspondências entre arquivos e tabelas do banco de dados.
    
    Args:
        extracted_files: Lista de arquivos extraídos
        database_tables: Lista de tabelas do banco de dados
    
    Returns:
        Dicionário mapeando tabelas para arquivos de dados correspondentes
    """
    # Filtra apenas arquivos .txt que não são layouts
    data_files = [f for f in extracted_files if f.endswith('.txt') and '_layout' not in f]
    layout_files = [f for f in extracted_files if f.endswith('.txt') and '_layout' in f]
    
    table_file_matches = {}
    unmatched_files = []
    
    for table in database_tables:
        # Procura arquivo que corresponda ao nome da tabela
        matching_data_file = next((f for f in data_files if table in f.lower()), None)
        matching_layout_file = next((f for f in layout_files if table in f.lower()), None)
        
        if matching_data_file and matching_layout_file:
            table_file_matches[table] = {
                'data_file': matching_data_file,
                'layout_file': matching_layout_file
            }
        else:
            unmatched_files.append(table)
    
    # Remove arquivos correspondentes das listas
    for match in table_file_matches.values():
        if match['data_file'] in data_files:
            data_files.remove(match['data_file'])
        if match['layout_file'] in layout_files:
            layout_files.remove(match['layout_file'])
    
    # Adiciona arquivos não correspondidos
    unmatched_files.extend(data_files)
    
    logger.info(f"Tabelas correspondidas: {list(table_file_matches.keys())}")
    logger.info(f"Arquivos/Tabelas não correspondidos: {unmatched_files}")
    
    return {
        'matched_tables': table_file_matches,
        'unmatched_files': unmatched_files
    }

def extract_zip_file(zip_path: str) -> Dict[str, Any]:
    """
    Extrai o conteúdo de um arquivo ZIP e identifica correspondências de tabelas.
    
    Returns:
        Dicionário com arquivos correspondidos e não correspondidos
    """
    temp_dir = None
    try:
        if not is_valid_zip(zip_path):
            logger.error(f"Arquivo ZIP inválido ou não encontrado: {zip_path}")
            return {'error': 'Invalid ZIP file'}
        
        # Cria diretório temporário para extração
        temp_dir = create_temp_dir()
        
        # Extrai o arquivo ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Lista arquivos extraídos
        extracted_files = os.listdir(temp_dir)
        
        # Recupera tabelas do banco de dados
        database_tables = get_database_tables()
        
        # Encontra correspondências
        matches = match_files_to_tables(extracted_files, database_tables)
        
        # Adiciona informações do diretório temporário
        matches['temp_dir'] = temp_dir
        
        logger.info(f"Correspondências encontradas: {matches}")
        return matches
    
    except Exception as e:
        logger.error(f"Erro ao extrair o arquivo ZIP: {str(e)}")
        if temp_dir:
            remove_temp_dir(temp_dir)
        return {'error': str(e)}

def process_file_upload(zip_path: str) -> Dict[str, Any]:
    """
    Processa o upload de um arquivo ZIP com foco em sincronização de dados.
    
    Args:
        zip_path: Caminho do arquivo ZIP
        
    Returns:
        Dicionário com resultado do processamento
    """
    try:
        # Extrai arquivos do ZIP e encontra correspondências
        extraction_result = extract_zip_file(zip_path)
        
        if 'error' in extraction_result:
            return {
                "success": False, 
                "message": extraction_result['error']
            }
        
        # Prepara resultado final
        results = {
            "synchronized_tables": [],
            "unmatched_files": extraction_result['unmatched_files']
        }
        
        # Sincroniza dados para tabelas correspondidas
        synchronized_tables = sync_data_for_matched_tables(
            extraction_result.get('matched_tables', {}), 
            extraction_result['temp_dir']
        )
        
        results['synchronized_tables'] = synchronized_tables
        
        # Remove diretório temporário
        remove_temp_dir(extraction_result['temp_dir'])
        
        return {
            "success": all(table['status'] == 'success' for table in results['synchronized_tables']),
            "details": results
        }
    
    except Exception as e:
        logger.error(f"Erro durante o processamento: {str(e)}")
        return {
            "success": False, 
            "message": f"Erro inesperado: {str(e)}"
        }