import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    """configurações gerais do Flask e do banco de dados."""
    # debug
    DEBUG = False

    # restrição de acesso
    SERVER_NAME = os.getenv("SERVER_NAME", "localhost:5000")

    # segurança de cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True

    # origens permitidas para CORS (separadas por vírgula no .env)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost").split(",")

    # configurações do banco de dados
    DB_USER = os.getenv("DB_USER", "usuario")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "senha")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "banco")
    DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "public")

    # uRL de conexão SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Porta do Flask
    FLASK_PORT = int(os.getenv("FLASK_PORT", 8080))
