import os
import uuid
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.services.vector_store import search_vector
from app.services.feature_extractor import extract_features

search_bp = Blueprint("search", __name__)

@search_bp.route("/search", methods=["POST"])
def search():
    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify({"error": "image is required"}), 400

    os.makedirs("uploads", exist_ok=True)
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"error": "invalid filename"}), 400
    path = os.path.join("uploads", f"{uuid.uuid4().hex}_{filename}")
    file.save(path)

    features = extract_features(path)
    results = search_vector(features["embed"])

    return jsonify(results)
