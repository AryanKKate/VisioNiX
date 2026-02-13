import os
import numpy as np
from flask import Blueprint, request, jsonify
from app.services.feature_extractor import extract_features
from app.services.vector_store import add_vector

features_bp = Blueprint("features", __name__)

@features_bp.route("/extract", methods=["POST"])
def extract():
    file = request.files["image"]

    os.makedirs("uploads", exist_ok=True)
    path = os.path.join("uploads", file.filename)
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
