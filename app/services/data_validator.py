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
    Validates if the layout corresponds to the database table structure with strict checks.
    """
    try:
        def map_oracle_to_postgres(oracle_type: str) -> str:
            type_mapping = {
                'VARCHAR2': 'character varying',
                'NUMBER': 'numeric',
                'CHAR': 'character',
                'DATE': 'date'
            }
            return type_mapping.get(oracle_type, oracle_type.lower())
        
        with SessionLocal() as session:
            query = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = :table AND table_schema = :schema
                ORDER BY ordinal_position
            """)
            
            result = session.execute(query, {
                'table': table_name, 
                'schema': DATABASE_SCHEMA
            })
            db_columns = [(row.column_name, row.data_type) for row in result]
        
        # More strict comparisons
        if len(layout_columns) != len(db_columns):
            logger.error(f"Column count mismatch for {table_name}. Layout: {len(layout_columns)}, Database: {len(db_columns)}")
            return False
        
        for (layout_col, (db_col, db_type)), index in zip(layout_columns, db_columns):
            # Ensure column names match exactly
            if layout_col['Coluna'].lower() != db_col.lower():
                logger.error(f"Column name mismatch at position {index}. Layout: {layout_col['Coluna']}, Database: {db_col}")
                return False
            
            # More precise type mapping and comparison
            mapped_layout_type = map_oracle_to_postgres(layout_col['Tipo'])
            if not db_type.lower().startswith(mapped_layout_type):
                logger.error(f"Column type mismatch for {db_col}. Layout: {layout_col['Tipo']} ({mapped_layout_type}), Database: {db_type}")
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Schema validation error for {table_name}: {str(e)}")
        return False

def validate_fixed_width_data(data_file_path: str, layout_columns: List[Dict[str, Any]], encoding: str = None) -> bool:
    """
    Valida o arquivo de dados de largura fixa.
    
    Args:
        data_file_path: Caminho do arquivo de dados
        layout_columns: Informações do layout
        encoding: Encoding do arquivo (opcional)
        
    Returns:
        Booleano indicando se os dados estão no formato correto
    """
    # Lista de possíveis encodings para tentar
    possible_encodings = [
        encoding,  # Primeiro, tenta o encoding fornecido
        'utf-8', 
        'iso-8859-1', 
        'windows-1252', 
        'latin1'
    ]
    
    # Remove None do início da lista
    possible_encodings = [enc for enc in possible_encodings if enc is not None]
    
    for current_encoding in possible_encodings:
        try:
            with open(data_file_path, 'r', encoding=current_encoding) as file:
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
            
            # Se chegou até aqui, a validação com este encoding foi bem-sucedida
            if current_encoding != encoding:
                logger.info(f"Usando encoding: {current_encoding}")
            return True
        
        except UnicodeDecodeError:
            # Continua para o próximo encoding se houver erro de decodificação
            continue
        except Exception as e:
            logger.error(f"Erro na validação dos dados: {str(e)}")
            return False
    
    # Se nenhum encoding funcionou
    logger.error("Não foi possível decodificar o arquivo com os encodings testados")
    return False

def parse_fixed_width_data(data_file_path: str, layout_columns: List[Dict[str, Any]], encoding: str = None) -> List[Dict[str, Any]]:
    """
    Converte arquivo de largura fixa para lista de dicionários.
    
    Args:
        data_file_path: Caminho do arquivo de dados
        layout_columns: Informações do layout
        encoding: Encoding do arquivo (opcional)
        
    Returns:
        Lista de dicionários com os registros
    """
    # Lista de possíveis encodings para tentar
    possible_encodings = [
        encoding,  # Primeiro, tenta o encoding fornecido
        'utf-8', 
        'iso-8859-1', 
        'windows-1252', 
        'latin1'
    ]
    
    # Remove None do início da lista
    possible_encodings = [enc for enc in possible_encodings if enc is not None]
    
    for current_encoding in possible_encodings:
        try:
            records = []
            
            with open(data_file_path, 'r', encoding=current_encoding) as file:
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
            
            # Se chegou até aqui, a validação com este encoding foi bem-sucedida
            if current_encoding != encoding:
                logger.info(f"Usando encoding: {current_encoding}")
            return records
        
        except UnicodeDecodeError:
            # Continua para o próximo encoding se houver erro de decodificação
            continue
        except Exception as e:
            logger.error(f"Erro na interpretação dos dados: {str(e)}")
            return []
    
    # Se nenhum encoding funcionou
    logger.error("Não foi possível decodificar o arquivo com os encodings testados")
    return []