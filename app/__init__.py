from flask import Flask
from config import DATABASE_URL

def create_app():
    """
    Factory function para criar e configurar a aplicação Flask.
    """
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Registrar blueprints (rotas)
    from app.routes.api import api_bp
    app.register_blueprint(api_bp)

    return app