from flask import Blueprint, request, jsonify
from app.services.vector_store import search_vector
from app.services.feature_extractor import extract_features

search_bp = Blueprint("search", __name__)

@search_bp.route("/search", methods=["POST"])
def search():
    file = request.files["image"]
    file.save(file.filename)

    features = extract_features(file.filename)
    results = search_vector(features["embedding"])

    return jsonify(results)
