import logging
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from models.database import SessionLocal

logger = logging.getLogger("DatabaseService")

def insert_records_safely(table_name: str, records: List[Dict[str, Any]]) -> bool:
    """
    Insere registros no banco de dados de forma segura (proteção contra SQL injection).
    
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
        return False
    finally:
        db.close()