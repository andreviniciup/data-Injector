import logging
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.models.database import SessionLocal
from app.utils.async_utils import batch_process
import asyncio

logger = logging.getLogger("DatabaseService")

def insert_records_safely_sync(table_name: str, records: List[Dict[str, Any]]) -> bool:
    try:
        db = SessionLocal()
        logger.info(f"Iniciando inserção em {table_name} ({len(records)} registros)")
        
        if not records:
            logger.warning("Nenhum registro para inserir")
            return True

        # Log das colunas
        logger.info(f"Colunas detectadas: {list(records[0].keys())}")
        
        for record in records:
            columns = ", ".join(record.keys())
            values = ", ".join([f":{key}" for key in record.keys()])
            query = text(f"INSERT INTO {table_name} ({columns}) VALUES ({values})")
            db.execute(query, record)
        
        db.commit()
        logger.info(f"Inserção concluída em {table_name}")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Erro em {table_name}: {str(e)}")
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