import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do banco de dados
DB_USER = os.getenv("DB_USER", "usuario")
DB_PASSWORD = os.getenv("DB_PASSWORD", "senha")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "banco")

# Monta a URL de conexão
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "public")

# Porta do Flask
FLASK_PORT = int(os.getenv("FLASK_PORT", 8080))