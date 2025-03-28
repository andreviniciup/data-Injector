from flask import Blueprint, request, jsonify, render_template
from app.services.file_processor import process_file_upload
from app.services.error_handler import ErrorHandler
import tempfile
import os
import asyncio

# Cria um Blueprint para as rotas da API
api_bp = Blueprint('api', __name__)

error_handler = ErrorHandler()

@api_bp.route('/')
def index():
    """
    View para renderizar a página inicial (index.html).
    """
    return render_template('index.html')

@api_bp.route('/upload', methods=['POST'])
def upload_file():
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
        # Processa o arquivo de forma síncrona
        result = process_file_upload(temp_zip)
        return jsonify(result)
    
    except Exception as e:
        error_handler.log_error(f"Erro durante o processamento: {str(e)}")
        return jsonify({"success": False, "message": f"Erro durante o processamento: {str(e)}"})
    
    finally:
        # Remove o arquivo temporário
        if os.path.exists(temp_zip):
            os.remove(temp_zip)