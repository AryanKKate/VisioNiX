from typing import Any, Optional

from flask import Blueprint, jsonify, request
from supabase import AuthApiError

from app.services.supabase_client import get_supabase_client
from app.services.training_jobs import (
    create_training_job,
    get_training_job,
    list_training_jobs,
    normalize_training_payload,
)
from app.services.training_runner import deploy_training_job, enqueue_training_job


training_bp = Blueprint("training", __name__, url_prefix="/training")


def _extract_bearer_token(auth_header: str) -> Optional[str]:
    if not auth_header:
        return None

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def _get_user_from_request() -> tuple[Any | None, tuple[Any, int] | None]:
    token = _extract_bearer_token(request.headers.get("Authorization", ""))
    if not token:
        return None, (jsonify({"error": "Bearer token is required"}), 401)

    if not isinstance(token, str) or token.count(".") != 2:
        return None, (jsonify({"error": "Malformed access token"}), 401)

    try:
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            return None, (jsonify({"error": "Invalid user session"}), 401)
        return user_response.user, None
    except (AuthApiError, ValueError) as exc:
        return None, (jsonify({"error": str(exc)}), 401)
    except Exception as exc:
        return None, (jsonify({"error": f"unexpected error: {exc}"}), 500)


@training_bp.route("/jobs", methods=["POST"])
def create_job():
    user, error = _get_user_from_request()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    normalized_payload, validation_errors = normalize_training_payload(payload)
    if validation_errors:
        return jsonify({"error": "validation_error", "details": validation_errors}), 400

    job, storage_backend = create_training_job(user.id, normalized_payload)
    worker_started = enqueue_training_job(job)

    return jsonify({"job": job, "storage": storage_backend, "worker_started": worker_started}), 201


@training_bp.route("/jobs", methods=["GET"])
def list_jobs():
    user, error = _get_user_from_request()
    if error:
        return error

    jobs, storage_backend = list_training_jobs(user.id)
    return jsonify({"jobs": jobs, "storage": storage_backend})


@training_bp.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id: str):
    user, error = _get_user_from_request()
    if error:
        return error

    job, storage_backend = get_training_job(user.id, job_id)
    if not job:
        return jsonify({"error": "job not found", "id": job_id}), 404

    return jsonify({"job": job, "storage": storage_backend})


@training_bp.route("/jobs/<job_id>/deploy", methods=["POST"])
def deploy_job(job_id: str):
    user, error = _get_user_from_request()
    if error:
        return error

    try:
        result = deploy_training_job(user_id=user.id, job_id=job_id)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
