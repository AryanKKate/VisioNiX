import os
import json
import time
import uuid
import logging
from typing import Any
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from app.services.feature_extractor import extract_features
from app.services.ollama_service import generate_with_ollama, check_ollama_health

llm_bp = Blueprint("llm", __name__)
logger = logging.getLogger(__name__)
_REASONING_SESSIONS: dict[str, dict[str, Any]] = {}


def _persist_describe_run(payload: dict) -> None:
    log_path = os.getenv("DESCRIBE_RUNS_LOG_PATH", "logs/describe_runs.jsonl")
    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _prune_reasoning_sessions() -> None:
    max_sessions = int(os.getenv("REASONING_MAX_SESSIONS", "25"))
    if len(_REASONING_SESSIONS) <= max_sessions:
        return

    ordered = sorted(
        _REASONING_SESSIONS.items(),
        key=lambda item: item[1].get("updated_at", 0),
    )
    remove_count = len(_REASONING_SESSIONS) - max_sessions
    for session_id, _ in ordered[:remove_count]:
        _REASONING_SESSIONS.pop(session_id, None)


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


@llm_bp.route("/reason", methods=["POST"])
def reason_over_image():
    request_id = str(uuid.uuid4())
    start_ts = time.time()

    prompt = (request.form.get("prompt") or "").strip()
    model = (request.form.get("model") or "").strip() or None
    session_id = (request.form.get("session_id") or "").strip() or None

    if not prompt:
        return jsonify({"error": "Missing prompt", "request_id": request_id}), 400

    session: dict[str, Any] | None = None
    created_new_session = False

    if session_id:
        session = _REASONING_SESSIONS.get(session_id)
        if not session:
            return jsonify(
                {
                    "error": "Invalid session_id. Start a new reasoning session with an image.",
                    "request_id": request_id,
                }
            ), 404
    else:
        if "image" not in request.files:
            return jsonify(
                {
                    "error": "Missing image file. Required when session_id is not provided.",
                    "request_id": request_id,
                }
            ), 400

        file = request.files["image"]
        if not file.filename:
            return jsonify({"error": "Empty file name", "request_id": request_id}), 400

        os.makedirs("uploads", exist_ok=True)
        original_filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        image_path = os.path.join("uploads", unique_filename)
        file.save(image_path)

        features = extract_features(image_path)
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "image_name": original_filename,
            "image_path": image_path,
            "features": features,
            "history": [],
            "created_at": time.time(),
            "updated_at": time.time(),
            "model": model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b"),
        }
        _REASONING_SESSIONS[session_id] = session
        _prune_reasoning_sessions()
        created_new_session = True

    assert session is not None
    assert session_id is not None

    if model:
        session["model"] = model
    active_model = session.get("model") or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b")

    history_window = int(os.getenv("REASONING_HISTORY_WINDOW", "8"))
    history_for_model = list(session.get("history", []))[-history_window:]

    try:
        llm_text = generate_with_ollama(
            features=session["features"],
            image_path=session["image_path"],
            user_prompt=prompt,
            ollama_model=active_model,
            conversation_history=history_for_model,
        )
    except Exception as exc:
        elapsed_ms = int((time.time() - start_ts) * 1000)
        event = {
            "event": "reason_failed",
            "request_id": request_id,
            "session_id": session_id,
            "model": active_model,
            "latency_ms": elapsed_ms,
            "error": str(exc),
            "status": "error",
        }
        logger.error(json.dumps(event, ensure_ascii=True))
        _persist_describe_run(event)
        return jsonify(
            {
                "error": "Ollama reasoning failed",
                "details": str(exc),
                "request_id": request_id,
                "session_id": session_id,
                "model": active_model,
                "timing_ms": elapsed_ms,
            }
        ), 502

    session_history = session.setdefault("history", [])
    session_history.append(
        {
            "user": prompt,
            "assistant": llm_text,
            "timestamp": time.time(),
        }
    )
    max_history_store = int(os.getenv("REASONING_MAX_HISTORY_TURNS", "30"))
    if len(session_history) > max_history_store:
        session["history"] = session_history[-max_history_store:]

    session["updated_at"] = time.time()

    elapsed_ms = int((time.time() - start_ts) * 1000)
    turn_index = len(session["history"])
    run_record = {
        "event": "reason_success",
        "request_id": request_id,
        "session_id": session_id,
        "model": active_model,
        "image_name": session.get("image_name"),
        "prompt": prompt,
        "turn_index": turn_index,
        "latency_ms": elapsed_ms,
        "status": "ok",
    }
    logger.info(json.dumps(run_record, ensure_ascii=True))
    _persist_describe_run(run_record)

    return jsonify(
        {
            "request_id": request_id,
            "session_id": session_id,
            "model": active_model,
            "llm_response": llm_text,
            "turn_index": turn_index,
            "created_new_session": created_new_session,
            "timing_ms": elapsed_ms,
        }
    )


@llm_bp.route("/reason/end", methods=["POST"])
def end_reason_session():
    payload = request.get_json(silent=True) or {}
    session_id = (payload.get("session_id") or request.form.get("session_id") or "").strip()

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    removed = _REASONING_SESSIONS.pop(session_id, None)
    return jsonify({"status": "ok", "ended": bool(removed), "session_id": session_id})
