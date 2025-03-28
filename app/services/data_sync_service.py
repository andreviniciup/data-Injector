import os
import logging
import re
from typing import List, Dict, Any
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, Base
from app.services.data_validator import parse_layout_file, parse_fixed_width_data
from app.services.error_handler import ErrorHandler
from app.services.database_service import insert_records_safely_sync
from config import DATABASE_SCHEMA

logger = logging.getLogger("DataSyncService")

class DataSyncService:
    def __init__(self):
        self.logger = logging.getLogger("DataSyncService")
        self.error_handler = ErrorHandler()
        self.processed_layouts = set()

    def _get_table_columns(self, session: Session, table_name: str) -> Dict[str, str]:
        inspector = inspect(session.bind)
        columns = inspector.get_columns(table_name, schema=DATABASE_SCHEMA)
        return {col['name']: str(col['type']) for col in columns}

    def _get_existing_records(self, session: Session, table_name: str) -> List[Dict]:
        try:
            query = text(f"SELECT * FROM {DATABASE_SCHEMA}.{table_name}")
            result = session.execute(query)
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            self.logger.error(f"Erro ao buscar registros em {table_name}: {str(e)}")
            return []

    def _compare_data_and_layout(self, table_name: str, layout_columns: List[Dict[str, Any]], db_columns: Dict[str, str]) -> Dict[str, Any]:
        differences = {
            'missing_columns': [],
            'extra_columns': [],
            'type_mismatches': []
        }

        def get_base_type(db_type: str) -> str:
            return re.sub(r'\(.*\)', '', str(db_type)).upper()

        def map_oracle_to_sqlalchemy(oracle_type: str) -> str:
            type_mapping = {
                'VARCHAR2': 'VARCHAR',
                'NUMBER': 'NUMERIC',
                'CHAR': 'CHAR',
                'DATE': 'DATE'
            }
            return type_mapping.get(oracle_type.split('(')[0].upper(), oracle_type)

        layout_column_names = [col['Coluna'] for col in layout_columns]
        
        # Verifica colunas faltantes
        for col in layout_columns:
            column_name = col['Coluna']
            if not any(db_col.lower() == column_name.lower() for db_col in db_columns.keys()):
                differences['missing_columns'].append(column_name)
                self.logger.warning(f"Coluna faltante: {table_name}.{column_name}")

        # Verifica colunas extras
        for db_col in db_columns.keys():
            if db_col.lower() not in [col.lower() for col in layout_column_names]:
                differences['extra_columns'].append(db_col)
                self.logger.warning(f"Coluna extra: {table_name}.{db_col}")

        # Verificação de tipos
        for col in layout_columns:
            column_name = col['Coluna']
            db_col_name = next((db_col for db_col in db_columns.keys() if db_col.lower() == column_name.lower()), None)
            if not db_col_name:
                continue

            db_type = db_columns[db_col_name]
            layout_type = map_oracle_to_sqlalchemy(col['Tipo'])
            db_base_type = get_base_type(db_type)
            layout_base_type = layout_type.upper()

            if db_base_type != layout_base_type:
                differences['type_mismatches'].append({
                    'column': column_name,
                    'layout_type': layout_type,
                    'db_type': str(db_type)
                })
                self.logger.warning(f"Tipo incompatível: {table_name}.{column_name} (Layout: {layout_base_type}, Banco: {db_base_type})")

        return differences

    def sync_table_data(self, table_name: str, data_file_path: str, layout_file_path: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"Processando tabela: {table_name}")
            self.processed_layouts.add(layout_file_path)

            # Parse de dados
            layout_columns = parse_layout_file(layout_file_path)
            records = parse_fixed_width_data(data_file_path, layout_columns)
            if not records:
                return {'status': 'error', 'message': 'Nenhum dado válido encontrado'}

            with SessionLocal() as session:
                # Comparação de schema
                db_columns = self._get_table_columns(session, table_name)
                schema_diff = self._compare_data_and_layout(table_name, layout_columns, db_columns)
                if schema_diff['missing_columns']:
                    return {'status': 'error', 'message': f"Colunas faltantes: {schema_diff['missing_columns']}"}

                # Busca registros existentes
                existing_records = self._get_existing_records(session, table_name)
                new_records = []

                # Comparação de dados
                primary_key = 'co_procedimento'  # Ajuste conforme a tabela
                existing_ids = {str(r[primary_key]) for r in existing_records} if existing_records else set()

                for record in records:
                    record_id = str(record.get(primary_key))
                    if not record_id:
                        continue
                    if record_id not in existing_ids:
                        new_records.append(record)
                        self.logger.info(f"Novo registro detectado em {table_name}: ID {record_id}")

                # Insere novos registros
                if new_records:
                    self.logger.info(f"Inserindo {len(new_records)} registros em {table_name}")
                    success = insert_records_safely_sync(table_name, new_records)
                    if not success:
                        return {'status': 'error', 'message': 'Falha na inserção'}

                return {
                    'status': 'success',
                    'table': table_name,
                    'new_records': len(new_records),
                    'processed_layout': layout_file_path
                }

        except Exception as e:
            error_msg = f"Erro em {table_name}: {str(e)}"
            self.logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}

def sync_data_for_matched_tables(matched_tables: Dict[str, Dict[str, str]], temp_dir: str) -> List[Dict[str, Any]]:
    sync_service = DataSyncService()
    results = []
    
    for table, files in matched_tables.items():
        data_file = os.path.join(temp_dir, files['data_file'])
        layout_file = os.path.join(temp_dir, files['layout_file'])
        
        result = sync_service.sync_table_data(table, data_file, layout_file)
        results.append(result)
    
    logger.info(f"Layouts processados: {sync_service.processed_layouts}")
    return results