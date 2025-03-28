import logging
from typing import List, Dict, Any
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, Base
from app.services.data_validator import parse_layout_file, parse_fixed_width_data
from app.services.error_handler import ErrorHandler
from config import DATABASE_SCHEMA

class DataSyncService:
    def __init__(self):
        self.logger = logging.getLogger("DataSyncService")
        self.error_handler = ErrorHandler()

    def _get_table_columns(self, session: Session, table_name: str) -> Dict[str, str]:
        """
        Recupera os nomes e tipos das colunas de uma tabela.
        
        Args:
            session: Sessão do SQLAlchemy
            table_name: Nome da tabela
        
        Returns:
            Dicionário com nomes e tipos das colunas
        """
        inspector = inspect(session.bind)
        columns = inspector.get_columns(table_name, schema=DATABASE_SCHEMA)
        return {col['name']: col['type'] for col in columns}

    def _compare_data_and_layout(self, 
                                  table_name: str, 
                                  layout_columns: List[Dict[str, Any]], 
                                  db_columns: Dict[str, str]) -> Dict[str, Any]:
        """
        Compara layout do arquivo com colunas do banco de dados.
        
        Args:
            table_name: Nome da tabela
            layout_columns: Colunas do layout
            db_columns: Colunas do banco de dados
        
        Returns:
            Dicionário com diferenças encontradas
        """
        differences = {
            'missing_columns': [],
            'extra_columns': [],
            'type_mismatches': []
        }

        # Mapeamento de tipos Oracle para SQLAlchemy
        def map_oracle_to_sqlalchemy(oracle_type: str) -> str:
            type_mapping = {
                'VARCHAR2': 'VARCHAR',
                'NUMBER': 'NUMERIC',
                'CHAR': 'CHAR',
                'DATE': 'DATE'
            }
            return type_mapping.get(oracle_type, oracle_type)

        # Verifica colunas do layout
        layout_column_names = [col['Coluna'] for col in layout_columns]
        
        # Colunas faltantes
        for col in layout_columns:
            column_name = col['Coluna']
            if column_name.lower() not in [db_col.lower() for db_col in db_columns.keys()]:
                differences['missing_columns'].append(column_name)
                self.logger.warning(f"Tabela {table_name}: Coluna '{column_name}' não encontrada no banco de dados")

        # Colunas extras no banco de dados
        for db_col in db_columns.keys():
            if db_col.lower() not in [col.lower() for col in layout_column_names]:
                differences['extra_columns'].append(db_col)
                self.logger.warning(f"Tabela {table_name}: Coluna '{db_col}' não presente no layout")

        # Verificação de tipos
        for col in layout_columns:
            column_name = col['Coluna']
            if column_name.lower() in [db_col.lower() for db_col in db_columns.keys()]:
                db_type = db_columns[column_name]
                layout_type = map_oracle_to_sqlalchemy(col['Tipo'])
                
                # Comparação simples de tipos 
                if str(db_type).upper() != layout_type.upper():
                    differences['type_mismatches'].append({
                        'column': column_name,
                        'layout_type': layout_type,
                        'db_type': str(db_type)
                    })
                    self.logger.warning(f"Tabela {table_name}: Tipo de coluna '{column_name}' incompatível. Layout: {layout_type}, Banco: {db_type}")

        return differences

    def sync_table_data(self, 
                         table_name: str, 
                         data_file_path: str, 
                         layout_file_path: str) -> Dict[str, Any]:
        """
        Sincroniza dados de um arquivo com a tabela do banco de dados.
        
        Args:
            table_name: Nome da tabela
            data_file_path: Caminho do arquivo de dados
            layout_file_path: Caminho do arquivo de layout
        
        Returns:
            Resultado da sincronização
        """
        try:
            # Inicia log para esta tabela
            self.logger.info(f"Iniciando sincronização para tabela: {table_name}")
            
            # Lê o layout
            layout_columns = parse_layout_file(layout_file_path)
            if not layout_columns:
                error_msg = f"Falha ao interpretar layout para {table_name}"
                self.logger.error(error_msg)
                return {'status': 'error', 'message': error_msg}
            
            # Abre sessão do banco de dados
            with SessionLocal() as session:
                # Recupera colunas do banco de dados
                db_columns = self._get_table_columns(session, table_name)
                
                # Compara layout com banco de dados
                differences = self._compare_data_and_layout(table_name, layout_columns, db_columns)
                
                # Lê dados do arquivo
                records = parse_fixed_width_data(data_file_path, layout_columns)
                
                # TODO: Implementar lógica de atualização/inserção baseada nas diferenças
                # Isso pode incluir:
                # 1. Adicionar colunas faltantes
                # 2. Remover colunas extras
                # 3. Ajustar tipos de dados
                # 4. Inserir ou atualizar registros
                
                return {
                    'status': 'success',
                    'table': table_name,
                    'differences': differences,
                    'records_count': len(records)
                }
        
        except Exception as e:
            error_msg = f"Erro durante sincronização de {table_name}: {str(e)}"
            self.logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}

def sync_data_for_matched_tables(matched_tables: Dict[str, Dict[str, str]], temp_dir: str) -> List[Dict[str, Any]]:
    """
    Sincroniza dados para todas as tabelas correspondidas.
    
    Args:
        matched_tables: Dicionário de tabelas correspondidas
        temp_dir: Diretório temporário com arquivos
    
    Returns:
        Lista de resultados de sincronização
    """
    sync_service = DataSyncService()
    results = []
    
    for table, files in matched_tables.items():
        data_file_path = os.path.join(temp_dir, files['data_file'])
        layout_file_path = os.path.join(temp_dir, files['layout_file'])
        
        result = sync_service.sync_table_data(table, data_file_path, layout_file_path)
        results.append(result)
    
    return results