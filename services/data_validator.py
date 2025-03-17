import re
import logging
from typing import List, Dict, Any
from sqlalchemy import inspect
from models.database import engine

logger = logging.getLogger("DataValidator")

def parse_layout_file(layout_file_path: str) -> List[Dict[str, Any]]:
    """
    Lê e interpreta o arquivo de layout.
    
    Args:
        layout_file_path: Caminho para o arquivo de layout.
        
    Returns:
        Lista de dicionários com informações de cada coluna (nome e tipo).
    """
    try:
        layout_info = []
        with open(layout_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Assumindo que o formato é "NOME_COLUNA TIPO_DADO [TAMANHO]"
                parts = re.split(r'\s+', line, 1)
                if len(parts) >= 2:
                    column_name = parts[0].lower()
                    data_type = parts[1].lower()
                    
                    layout_info.append({
                        "column_name": column_name,
                        "data_type": data_type
                    })
        
        logger.info(f"Layout analisado: {len(layout_info)} colunas encontradas")
        return layout_info
        
    except Exception as e:
        logger.error(f"Erro ao interpretar o arquivo de layout: {str(e)}")
        return []