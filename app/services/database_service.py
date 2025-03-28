import logging
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.models.database import SessionLocal
from app.utils.async_utils import batch_process
import asyncio

logger = logging.getLogger("DatabaseService")

def insert_records_safely_sync(table_name: str, records: List[Dict[str, Any]]) -> bool:
    """
    Insere registros no banco de dados de forma síncrona.
    
    Args:
        table_name: Nome da tabela.
        records: Lista de dicionários com os registros.
        
    Returns:
        True se a operação for bem-sucedida, False caso contrário.
    """
    try:
        db = SessionLocal()
        
        for record in records:
            # Usa SQLAlchemy para evitar SQL injection
            columns = ", ".join(record.keys())
            values = ", ".join([f":{key}" for key in record.keys()])
            query = text(f"INSERT INTO {table_name} ({columns}) VALUES ({values})")
            db.execute(query, record)
        
        db.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Erro ao inserir registros: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

async def insert_records_safely(table_name: str, records: List[Dict[str, Any]]) -> bool:
    """
    Wrapper assíncrono para inserção síncrona de registros.
    
    Args:
        table_name: Nome da tabela.
        records: Lista de dicionários com os registros.
        
    Returns:
        True se a operação for bem-sucedida, False caso contrário.
    """
    return await asyncio.to_thread(insert_records_safely_sync, table_name, records)