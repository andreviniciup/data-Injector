from flask import Flask, request, jsonify
from services.file_processor import extract_zip_file
from services.data_validator import parse_layout_file
from services.database_service import insert_records_safely
from services.error_handler import ErrorHandler
import tempfile
import os

app = Flask(__name__)
error_handler = ErrorHandler()

@app.route('/upload', methods=['POST'])
async def upload_file():
    if 'file' not in request.files:
        error_handler.log_error("Nenhum arquivo enviado")
        return jsonify({"success": False, "message": "Nenhum arquivo enviado"})
    
    file = request.files['file']
    if file.filename == '':
        error_handler.log_error("Nome de arquivo vazio")
        return jsonify({"success": False, "message": "Nome de arquivo vazio"})
    
    if not file.filename.endswith('.zip'):
        error_handler.log_error("O arquivo deve ter extensão .zip")
        return jsonify({"success": False, "message": "O arquivo deve ter extensão .zip"})
    
    # Salva o arquivo temporariamente
    temp_zip = os.path.join(tempfile.gettempdir(), file.filename)
    file.save(temp_zip)
    
    try:
        # Processa o arquivo
        data_file, layout_file = extract_zip_file(temp_zip)
        if not data_file or not layout_file:
            error_handler.log_error("Falha ao extrair arquivos")
            return jsonify({"success": False, "message": "Falha ao extrair arquivos"})
        
        # Lê o layout
        layout_info = parse_layout_file(layout_file)
        if not layout_info:
            error_handler.log_error("Falha ao interpretar arquivo de layout")
            return jsonify({"success": False, "message": "Falha ao interpretar arquivo de layout"})
        
        # Insere registros (exemplo)
        records = [{"coluna1": "valor1", "coluna2": 123}]  # Substitua pelos dados reais
        success = await insert_records_safely("rl_procedimento_origem", records)
        
        return jsonify({"success": success, "message": "Processamento concluído"})
    
    except Exception as e:
        error_handler.log_error(f"Erro durante o processamento: {str(e)}")
        return jsonify({"success": False, "message": f"Erro durante o processamento: {str(e)}"})
    
    finally:
        # Remove o arquivo temporário
        if os.path.exists(temp_zip):
            os.remove(temp_zip)