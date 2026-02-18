from flask import Flask
from flask_cors import CORS
from app.routes.features import features_bp
from app.routes.search import search_bp
from app.routes.auth import auth_bp
from app.routes.llm import llm_bp
from app.routes.chat import chat_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    @app.get("/")
    def root():
        return {"status": "ok", "message": "VisioNiX backend is running"}

    app.register_blueprint(features_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(llm_bp)
    app.register_blueprint(chat_bp)

    return app

