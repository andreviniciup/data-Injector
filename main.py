from app import create_app
from config import FLASK_PORT, DEBUG

app = create_app()

if __name__ == "__main__":
    app.run(debug=DEBUG, port=FLASK_PORT)