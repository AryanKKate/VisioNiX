import os
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from app.services.feature_extractor import extract_features
from app.services.ollama_service import generate_with_ollama

llm_bp = Blueprint("llm", __name__)


@llm_bp.route("/describe", methods=["POST"])
def describe_image():
    if "image" not in request.files:
        return jsonify({"error": "Missing image file"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty file name"}), 400

    prompt = request.form.get("prompt")
    model = (request.form.get("model") or "").strip() or None

    os.makedirs("uploads", exist_ok=True)
    filename = secure_filename(file.filename)
    path = os.path.join("uploads", filename)
    file.save(path)

    features = extract_features(path)

    try:
        llm_text = generate_with_ollama(
            features=features,
            image_path=path,
            user_prompt=prompt,
            ollama_model=model,
        )
    except Exception as exc:
        return jsonify(
            {
                "error": "Ollama request failed",
                "details": str(exc),
                "model": model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
                "features": features,
            }
        ), 502

    return jsonify(
        {
            "model": model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
            "features": features,
            "llm_response": llm_text,
        }
    )
