import os
import uuid
import numpy as np
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.services.feature_extractor import extract_features
from app.services.vector_store import add_vector

features_bp = Blueprint("features", __name__)

@features_bp.route("/extract", methods=["POST"])
def extract():
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

    embedding_path = features["clip_embedding_path"]
    embedding = np.load(embedding_path)

    add_vector(embedding.tolist(), {
        "filename": file.filename,
        "caption": features["caption"],
        "objects": features["objects"],
        "scene": features["scene_labels"]
    })

    return jsonify(features)
