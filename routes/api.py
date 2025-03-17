from flask import Flask, request, jsonify
from services.file_processor import extract_zip_file
from services.data_validator import parse_layout_file
from services.database_service import insert_records_safely
import tempfile
import os

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Nenhum arquivo enviado"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Nome de arquivo vazio"})
    
    if not file.filename.endswith('.zip'):
        return jsonify({"success": False, "message": "O arquivo deve ter extensão .zip"})
    
    # Salva o arquivo temporariamente
    temp_zip = os.path.join(tempfile.gettempdir(), file.filename)
    file.save(temp_zip)
    
    # Processa o arquivo
    data_file, layout_file = extract_zip_file(temp_zip)
    if not data_file or not layout_file:
        return jsonify({"success": False, "message": "Falha ao extrair arquivos"})
    
    # Lê o layout
    layout_info = parse_layout_file(layout_file)
    if not layout_info:
        return jsonify({"success": False, "message": "Falha ao interpretar arquivo de layout"})
    
    # Insere registros (exemplo)
    records = [{"coluna1": "valor1", "coluna2": 123}]  # Substitua pelos dados reais
    success = insert_records_safely("rl_procedimento_origem", records)
    
    # Remove o arquivo temporário
    os.remove(temp_zip)
    
    return jsonify({"success": success, "message": "Processamento concluído"})