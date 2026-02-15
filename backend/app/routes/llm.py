import os
import json
import time
import uuid
import logging
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from app.services.feature_extractor import extract_features
from app.services.ollama_service import generate_with_ollama, check_ollama_health

llm_bp = Blueprint("llm", __name__)
logger = logging.getLogger(__name__)


def _persist_describe_run(payload: dict) -> None:
    log_path = os.getenv("DESCRIBE_RUNS_LOG_PATH", "logs/describe_runs.jsonl")
    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


@llm_bp.route("/llm/health", methods=["GET"])
def llm_health():
    model = (request.args.get("model") or "").strip() or None
    try:
        health = check_ollama_health(model)
        return jsonify(health)
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc), "model": model}), 502


@llm_bp.route("/describe", methods=["POST"])
def describe_image():
    request_id = str(uuid.uuid4())
    start_ts = time.time()

    if "image" not in request.files:
        return jsonify({"error": "Missing image file", "request_id": request_id}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty file name", "request_id": request_id}), 400

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
        elapsed_ms = int((time.time() - start_ts) * 1000)
        event = {
            "event": "describe_failed",
            "request_id": request_id,
            "model": model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
            "image_name": filename,
            "latency_ms": elapsed_ms,
            "error": str(exc),
            "status": "error",
        }
        logger.error(json.dumps(event, ensure_ascii=True))
        _persist_describe_run(event)
        return jsonify(
            {
                "error": "Ollama request failed",
                "details": str(exc),
                "model": model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
                "features": features,
                "request_id": request_id,
                "timing_ms": elapsed_ms,
            }
        ), 502

    elapsed_ms = int((time.time() - start_ts) * 1000)
    run_record = {
        "event": "describe_success",
        "request_id": request_id,
        "model": model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
        "image_name": filename,
        "prompt": prompt,
        "features": features,
        "llm_response": llm_text,
        "latency_ms": elapsed_ms,
        "status": "ok",
    }
    logger.info(json.dumps(run_record, ensure_ascii=True))
    _persist_describe_run(run_record)

    return jsonify(
        {
            "model": model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
            "features": features,
            "llm_response": llm_text,
            "request_id": request_id,
            "timing_ms": elapsed_ms,
        }
    )
