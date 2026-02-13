from flask import Flask
from flask_cors import CORS
from app.routes.features import features_bp
from app.routes.search import search_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(features_bp)
    app.register_blueprint(search_bp)

    return app
