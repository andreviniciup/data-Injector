import os
import logging
import re
from datetime import datetime
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
            # Get table structure
            inspector = inspect(session.bind)
            pk_constraint = inspector.get_pk_constraint(table_name, schema=DATABASE_SCHEMA)
            columns_info = inspector.get_columns(table_name, schema=DATABASE_SCHEMA)
            column_names = [col['name'] for col in columns_info]

            # Create columns string for query
            columns_str = ", ".join(column_names)

            # Execute query to get all records
            query = text(f"SELECT {columns_str} FROM {DATABASE_SCHEMA}.{table_name}")
            self.logger.info(f"Buscando registros existentes em {table_name}")
            result = session.execute(query)

            # Convert result to dictionary
            records = [dict(zip(column_names, row)) for row in result]
            self.logger.info(f"Encontrados {len(records)} registros existentes em {table_name}")

            return records
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
            self.logger.info(f"Iniciando sincronização da tabela: {table_name}")
            self.processed_layouts.add(layout_file_path)

            # Parse layout e dados
            layout_columns = parse_layout_file(layout_file_path)
            records = parse_fixed_width_data(data_file_path, layout_columns)
            if not records:
                self.logger.warning(f"Nenhum dado válido encontrado para {table_name}")
                return {'status': 'error', 'message': 'Nenhum dado válido encontrado'}

            # Detecta chave primária
            primary_key = None
            table_name_without_prefix = table_name.replace('tb_', '')

            # Procura por colunas CO_ que correspondam ao nome da tabela
            co_columns = [col['Coluna'] for col in layout_columns if col['Coluna'].upper().startswith('CO_')]
            matching_columns = [col for col in co_columns if table_name_without_prefix.upper() in col.upper()]

            if matching_columns:
                primary_key = matching_columns[0]
            elif co_columns:
                primary_key = co_columns[0]
            elif layout_columns:
                primary_key = layout_columns[0]['Coluna']
                self.logger.warning(f"Nenhuma coluna CO_ encontrada em {table_name}, usando primeira coluna como chave: {primary_key}")
            else:
                return {'status': 'error', 'message': f"Não foi possível determinar a chave primária para {table_name}"}

            self.logger.info(f"Usando chave primária: {primary_key} para tabela {table_name}")

            with SessionLocal() as session:
                try:
                    # Validação de schema
                    db_columns = self._get_table_columns(session, table_name)
                    schema_diff = self._compare_data_and_layout(table_name, layout_columns, db_columns)
                    if schema_diff['missing_columns']:
                        return {'status': 'error', 'message': f"Colunas faltantes em {table_name}: {schema_diff['missing_columns']}"}

                    # Busca registros existentes
                    existing_records = self._get_existing_records(session, table_name)
                    new_records = []
                    updated_records = []
                    unchanged_records = 0

                    # Comparação de dados - VERSÃO CORRIGIDA
                    existing_records_dict = {}
                    primary_key_lower = primary_key.lower()  # Converter para minúsculas para comparação

                    for record in existing_records:
                        # Procura a chave ignorando diferenças de maiúsculas/minúsculas
                        matching_key = next((k for k in record.keys() if k.lower() == primary_key_lower), None)

                        if matching_key and record[matching_key] is not None:
                            key_value = str(record[matching_key]).strip()
                            if key_value:
                                existing_records_dict[key_value] = record

                    self.logger.info(f"Mapeados {len(existing_records_dict)} registros existentes por chave primária '{primary_key}' em {table_name}")

                    # Add diagnostic sampling
                    if existing_records and len(existing_records) > 0:
                        sample_record = existing_records[0]
                        self.logger.info(f"Amostra de registro existente: {sample_record}")
                        sample_key = str(sample_record.get(primary_key, '')).strip() if sample_record.get(primary_key) is not None else None
                        self.logger.info(f"Valor de chave primária da amostra: '{sample_key}'")

                    # Replace the existing record comparison loop with this enhanced version
                    for i, record in enumerate(records):
                        # Procura a chave ignorando diferenças de maiúsculas/minúsculas
                        matching_key = next((k for k in record.keys() if k.lower() == primary_key_lower), None)

                        if not matching_key or record[matching_key] is None:
                            self.logger.warning(f"Registro sem valor para chave primária {primary_key} em {table_name}")
                            continue

                        record_id = str(record[matching_key]).strip()

                        # Add example record logging
                        if i < 3:
                            self.logger.info(f"Exemplo registro #{i} do arquivo: {primary_key}='{record_id}'")

                        if record_id not in existing_records_dict:
                            new_records.append(record)
                            if len(new_records) <= 3:
                                self.logger.info(f"Novo registro identificado em {table_name}: {primary_key}='{record_id}' (não encontrado no banco)")
                        else:
                            existing_record = existing_records_dict[record_id]
                            differences = {}

                            for key in record:
                                # Ignora a chave primária na verificação - ela já é usada para identificar o registro
                                if key.lower() == primary_key_lower:
                                    continue

                                file_value = record[key]
                                db_value = existing_record.get(key)

                                # Função para normalizar valores para comparação
                                def _normalize_value(value):
                                    """Normaliza valores para comparação consistente"""
                                    # Trata valores nulos
                                    if value is None:
                                        return ''
                                    
                                    # Converte para string e remove espaços
                                    if isinstance(value, (int, float)):
                                        # Para números, usa representação de string precisa
                                        if isinstance(value, int):
                                            return str(value)
                                        else:  # float
                                            # Remove zeros à direita e ponto decimal se for inteiro
                                            # Usa formatação para evitar problemas de precisão
                                            if value == int(value):  # É um float que representa um inteiro
                                                return str(int(value))
                                            # Formatação com precisão fixa para evitar diferenças de arredondamento
                                            s = f"{value:.10f}".rstrip('0').rstrip('.') if value != 0 else '0'
                                            return s
                                    elif isinstance(value, datetime):
                                        # Normaliza datas para formato ISO sem milissegundos
                                        return value.strftime('%Y-%m-%d %H:%M:%S')
                                    elif isinstance(value, str):
                                        # Para strings, normaliza removendo espaços extras e convertendo para minúsculas
                                        # Também remove caracteres não imprimíveis que podem causar problemas
                                        s = value
                                        # Remove caracteres de controle e espaços extras
                                        s = re.sub(r'[\x00-\x1F\x7F]', '', s)
                                        # Normaliza espaços múltiplos para um único espaço
                                        s = re.sub(r'\s+', ' ', s)
                                        # Remove espaços no início e fim e converte para minúsculas
                                        s = s.strip().lower()
                                        # Tenta converter para número se parecer um número
                                        if re.match(r'^-?\d+(\.\d+)?$', s):
                                            try:
                                                if '.' in s:
                                                    num = float(s)
                                                    if num == int(num):  # É um float que representa um inteiro
                                                        return str(int(num))
                                                    return f"{num:.10f}".rstrip('0').rstrip('.')
                                                else:
                                                    return str(int(s))
                                            except (ValueError, TypeError):
                                                pass
                                        return s
                                    else:
                                        # Para outros tipos, converte para string e normaliza
                                        s = str(value)
                                        s = re.sub(r'[\x00-\x1F\x7F]', '', s)
                                        s = re.sub(r'\s+', ' ', s)
                                        return s.strip().lower()
                                
                                # Normaliza os valores para comparação
                                file_norm = _normalize_value(file_value)
                                db_norm = _normalize_value(db_value)
                                
                                # Se ambos forem vazios, são considerados iguais
                                if not file_norm and not db_norm:
                                    continue
                                    
                                # Tenta comparação numérica para maior precisão
                                numeric_equal = False
                                try:
                                    # Verifica se ambos parecem ser números
                                    file_is_numeric = re.match(r'^-?\d+(\.\d+)?$', file_norm) and file_norm.strip()
                                    db_is_numeric = re.match(r'^-?\d+(\.\d+)?$', db_norm) and db_norm.strip()
                                    
                                    if file_is_numeric and db_is_numeric:
                                        # Converte para float para comparação numérica
                                        file_num = float(file_norm)
                                        db_num = float(db_norm)
                                        
                                        # Se ambos são inteiros ou representam inteiros
                                        if file_num == int(file_num) and db_num == int(db_num):
                                            # Compara como inteiros
                                            numeric_equal = int(file_num) == int(db_num)
                                        else:
                                            # Compara com tolerância para números de ponto flutuante
                                            # Usa tolerância relativa para números grandes
                                            abs_diff = abs(file_num - db_num)
                                            max_val = max(abs(file_num), abs(db_num))
                                            if max_val > 1.0:
                                                # Tolerância relativa para números grandes
                                                numeric_equal = abs_diff / max_val < 0.0000001
                                            else:
                                                # Tolerância absoluta para números pequenos
                                                numeric_equal = abs_diff < 0.0000001
                                        
                                        if numeric_equal:
                                            self.logger.info(f"Valores numericamente iguais: {file_num} e {db_num}")
                                except (ValueError, TypeError):
                                    # Se falhar na conversão, não é numérico
                                    numeric_equal = False
                                
                                # Se os valores são numericamente iguais, não registra diferença
                                if numeric_equal:
                                    continue
                                    
                                # Se os valores normalizados são iguais, não registra diferença
                                if file_norm == db_norm:
                                    continue
                                    
                                # Registra a diferença para atualização
                                differences[key] = file_value
                                # Log detalhado para depuração das diferenças
                                self.logger.info(f"Diferença detectada em {table_name}.{key}:")
                                self.logger.info(f"  Valor DB: '{db_value}' (tipo: {type(db_value).__name__})")
                                self.logger.info(f"  Valor Arquivo: '{file_value}' (tipo: {type(file_value).__name__})")
                                self.logger.info(f"  Normalizado DB: '{db_norm}'")
                                self.logger.info(f"  Normalizado Arquivo: '{file_norm}'")

                            # Só atualiza se houver diferenças reais
                            if differences:
                                try:
                                    self.logger.info(f"Encontradas {len(differences)} diferenças no registro {primary_key}={record_id} em {table_name}")
                                    
                                    # Log detalhado das diferenças para depuração
                                    for key, new_value in differences.items():
                                        old_value = existing_record.get(key)
                                        self.logger.debug(f"  - Campo '{key}': Valor atual='{old_value}' → Novo valor='{new_value}'")
                                    
                                    # Construção da query de atualização
                                    set_clause = ", ".join([f"{k} = :{k}" for k in differences.keys()])
                                    update_query = text(
                                        f"UPDATE {DATABASE_SCHEMA}.{table_name} "
                                        f"SET {set_clause} "
                                        f"WHERE {primary_key} = :{primary_key}"
                                    )

                                    # Parâmetros para a query
                                    params = {**differences, primary_key: record_id}
                                    
                                    # Executa a atualização
                                    session.execute(update_query, params)
                                    updated_records.append(record_id)
                                    self.logger.info(f"Registro atualizado em {table_name}: {primary_key}={record_id} com {len(differences)} alterações")
                                except Exception as e:
                                    self.logger.error(f"Erro ao atualizar registro {record_id} em {table_name}: {str(e)}")
                                    raise
                            else:
                                unchanged_records += 1
                                if unchanged_records <= 3:  # Limita logs para não sobrecarregar
                                    self.logger.info(f"Registro sem alterações em {table_name}: {primary_key}={record_id}")

                    # Insere novos registros em lote
                    if new_records:
                        self.logger.info(f"Iniciando inserção de {len(new_records)} novos registros em {table_name}")
                        success = insert_records_safely_sync(table_name, new_records)
                        if not success:
                            raise Exception(f"Falha na inserção de registros em {table_name}")

                    session.commit()
                    self.logger.info(f"Sincronização concluída para {table_name}:")
                    self.logger.info(f"  - {len(new_records)} novos registros inseridos")
                    self.logger.info(f"  - {len(updated_records)} registros atualizados")
                    self.logger.info(f"  - {unchanged_records} registros sem alterações (já estavam atualizados)")

                    return {
                        'status': 'success',
                        'table': table_name,
                        'primary_key': primary_key,
                        'new_records': len(new_records),
                        'updated_records': len(updated_records),
                        'unchanged_records': unchanged_records,
                        'processed_layout': layout_file_path
                    }

                except Exception as e:
                    session.rollback()
                    raise e

        except Exception as e:
            error_msg = f"Erro na sincronização de {table_name}: {str(e)}"
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