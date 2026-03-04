import os
import uuid

import numpy as np
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from app.auth_jwt import require_supabase_auth
from app.services.db import get_model_by_id
from app.services.extraction_store import (
    add_extraction_record,
    delete_extraction_record,
    list_extraction_records,
)
from app.services.vector_store import add_vector


features_bp = Blueprint("features", __name__)
models_bp = Blueprint("models", __name__)


@models_bp.route("/models/<model_id>", methods=["GET"])
def fetch_model(model_id):
    model = get_model_by_id(model_id)

    if not model:
        return jsonify({"error": "Model not found"}), 404

    return jsonify(model)


@features_bp.route("/extract", methods=["POST"])
@require_supabase_auth
def extract():
    from app.services.feature_extractor import extract_features_with_model

    print("Incoming model_id:", request.form.get("model_id"))

    if "image" not in request.files:
        return jsonify({"error": "Missing image file"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty file name"}), 400

    model_id = request.form.get("model_id")
    if not model_id:
        return jsonify({"error": "model_id is required"}), 400

    user_id = request.user["sub"]

    os.makedirs("uploads", exist_ok=True)
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join("uploads", unique_filename)
    file.save(path)

    try:
        features = extract_features_with_model(path, model_id)
    except Exception as exc:
        return jsonify({"error": f"Model execution failed: {str(exc)}"}), 500

    embedding_path = features["clip_embedding_path"]
    embedding = np.load(embedding_path)

    add_vector(
        embedding.tolist(),
        {
            "filename": filename,
            "caption": features["caption"],
            "objects": features["objects"],
            "scene": features["scene_labels"],
            "model_id": model_id,
            "user_id": user_id,
        },
    )

    extraction_record = add_extraction_record(
        features=features,
        image_name=filename,
        image_path=path,
        source="extract",
    )

    response_payload = {
        **features,
        "id": extraction_record["id"],
        "timestamp": extraction_record["timestamp"],
        "source": extraction_record["source"],
    }

    return jsonify(response_payload)


@features_bp.route("/extractions", methods=["GET"])
def list_extractions():
    return jsonify(list_extraction_records())


@features_bp.route("/extractions/<extraction_id>", methods=["DELETE"])
def delete_extraction(extraction_id):
    was_deleted = delete_extraction_record(extraction_id)
    if not was_deleted:
        return jsonify({"error": "Extraction not found"}), 404
    return jsonify({"status": "ok", "deleted": True, "id": extraction_id})
