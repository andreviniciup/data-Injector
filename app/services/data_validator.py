import pandas as pd
import re
import logging
from typing import List, Dict, Any
from sqlalchemy import text
from app.models.database import engine, SessionLocal
from config import DATABASE_SCHEMA

logger = logging.getLogger("DataValidator")


def validate_database_schema(table_name: str, layout_columns: List[Dict[str, Any]]) -> bool:
    """
    Valida se o layout corresponde à estrutura da tabela no banco de dados.
    
    Args:
        table_name: Nome da tabela
        layout_columns: Colunas do layout
        
    Returns:
        Booleano indicando se o layout é válido
    """
    try:
        # Mapeamento de tipos de dados de Oracle para PostgreSQL
        def map_oracle_to_postgres(oracle_type: str) -> str:
            type_mapping = {
                'VARCHAR2': 'character varying',
                'NUMBER': 'numeric',
                'CHAR': 'character',
                'DATE': 'date'
            }
            return type_mapping.get(oracle_type, oracle_type.lower())
        
        # Obtém colunas do banco de dados
        with SessionLocal() as session:
            query = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = :table AND table_schema = :schema
            """)
            
            result = session.execute(query, {'table': table_name, 'schema': DATABASE_SCHEMA})
            db_columns = [(row.column_name, row.data_type) for row in result]
        
        # Verificações de layout
        if len(layout_columns) != len(db_columns):
            logger.error("Número de colunas diferente")
            return False
        
        for layout_col, (db_col, db_type) in zip(layout_columns, db_columns):
            # Compara nomes de colunas (ignorando case)
            if layout_col['Coluna'].lower() != db_col.lower():
                logger.error(f"Nome de coluna diferente: {layout_col['Coluna']} vs {db_col}")
                return False
            
            # Mapeia e compara tipos de dados
            mapped_layout_type = map_oracle_to_postgres(layout_col['Tipo'])
            if not db_type.startswith(mapped_layout_type):
                logger.error(f"Tipo de dados incompatível: {layout_col['Tipo']} vs {db_type}")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Erro na validação do schema: {str(e)}")
        return False

def parse_layout_file(layout_file_path: str) -> List[Dict[str, Any]]:
    """
    Lê e interpreta o arquivo de layout de largura fixa.
    
    Args:
        layout_file_path: Caminho para o arquivo de layout.
        
    Returns:
        Lista de dicionários com informações de cada coluna.
    """
    try:
        # Usa pandas para ler o CSV de layout
        layout_df = pd.read_csv(layout_file_path, sep=',')
        
        # Converte para lista de dicionários
        layout_info = layout_df.to_dict('records')
        
        logger.info(f"Layout analisado: {len(layout_info)} colunas encontradas")
        return layout_info
        
    except Exception as e:
        logger.error(f"Erro ao interpretar o arquivo de layout: {str(e)}")
        return []

def validate_database_schema(table_name: str, layout_columns: List[Dict[str, Any]]) -> bool:
    """
    Valida se o layout corresponde à estrutura da tabela no banco de dados.
    
    Args:
        table_name: Nome da tabela
        layout_columns: Colunas do layout
        
    Returns:
        Booleano indicando se o layout é válido
    """
    try:
        # Mapeamento de tipos de dados de Oracle para PostgreSQL
        def map_oracle_to_postgres(oracle_type: str) -> str:
            type_mapping = {
                'VARCHAR2': 'character varying',
                'NUMBER': 'numeric',
                'CHAR': 'character',
                'DATE': 'date'
            }
            return type_mapping.get(oracle_type, oracle_type.lower())
        
        # Obtém colunas do banco de dados
        with SessionLocal() as session:
            query = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = :table
            """)
            
            result = session.execute(query, {'table': table_name})
            db_columns = [(row.column_name, row.data_type) for row in result]
        
        # Verificações de layout
        if len(layout_columns) != len(db_columns):
            logger.error("Número de colunas diferente")
            return False
        
        for layout_col, (db_col, db_type) in zip(layout_columns, db_columns):
            # Compara nomes de colunas (ignorando case)
            if layout_col['Coluna'].lower() != db_col.lower():
                logger.error(f"Nome de coluna diferente: {layout_col['Coluna']} vs {db_col}")
                return False
            
            # Mapeia e compara tipos de dados
            mapped_layout_type = map_oracle_to_postgres(layout_col['Tipo'])
            if not db_type.startswith(mapped_layout_type):
                logger.error(f"Tipo de dados incompatível: {layout_col['Tipo']} vs {db_type}")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Erro na validação do schema: {str(e)}")
        return False

def validate_fixed_width_data(data_file_path: str, layout_columns: List[Dict[str, Any]]) -> bool:
    """
    Valida o arquivo de dados de largura fixa.
    
    Args:
        data_file_path: Caminho do arquivo de dados
        layout_columns: Informações do layout
        
    Returns:
        Booleano indicando se os dados estão no formato correto
    """
    try:
        with open(data_file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                # Remove newline e verifica comprimento total
                line = line.rstrip('\n')
                total_expected_length = int(layout_columns[-1]['Fim'])
                
                if len(line) != total_expected_length:
                    logger.error(f"Linha {line_num}: Comprimento incorreto. Esperado {total_expected_length}, encontrado {len(line)}")
                    return False
                
                # Valida cada coluna
                for col in layout_columns:
                    start = int(col['Inicio']) - 1
                    end = int(col['Fim'])
                    value = line[start:end]
                    
                    # Validações específicas por tipo
                    if col['Tipo'] == 'NUMBER':
                        try:
                            float(value.strip())
                        except ValueError:
                            logger.error(f"Linha {line_num}, Coluna {col['Coluna']}: Valor não numérico")
                            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Erro na validação dos dados: {str(e)}")
        return False

def parse_fixed_width_data(data_file_path: str, layout_columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converte arquivo de largura fixa para lista de dicionários.
    
    Args:
        data_file_path: Caminho do arquivo de dados
        layout_columns: Informações do layout
        
    Returns:
        Lista de dicionários com os registros
    """
    records = []
    
    with open(data_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            record = {}
            for col in layout_columns:
                start = int(col['Inicio']) - 1
                end = int(col['Fim'])
                value = line[start:end].strip()
                
                # Conversão de tipos
                if col['Tipo'] == 'NUMBER':
                    value = float(value) if value else None
                elif col['Tipo'] == 'VARCHAR2':
                    value = value
                elif col['Tipo'] == 'CHAR':
                    value = value
                
                record[col['Coluna']] = value
            
            records.append(record)
    
    return records