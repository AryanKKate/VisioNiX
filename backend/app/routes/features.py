import os
import uuid

import numpy as np
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from app.services.feature_extractor import extract_features
from app.services.extraction_store import (
    add_extraction_record,
    delete_extraction_record,
    list_extraction_records,
)
from app.services.vector_store import add_vector

features_bp = Blueprint("features", __name__)


@features_bp.route("/extract", methods=["POST"])
def extract():
    if "image" not in request.files:
        return jsonify({"error": "Missing image file"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty file name"}), 400

    os.makedirs("uploads", exist_ok=True)
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join("uploads", unique_filename)
    file.save(path)

    features = extract_features(path)

    embedding_path = features["clip_embedding_path"]
    embedding = np.load(embedding_path)

    add_vector(embedding.tolist(), {
        "filename": filename,
        "caption": features["caption"],
        "objects": features["objects"],
        "scene": features["scene_labels"]
    })

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
