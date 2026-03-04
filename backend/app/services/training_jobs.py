import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.services.supabase_client import get_supabase_client


ALLOWED_TASK_TYPES = {"classification", "detection", "segmentation"}
ALLOWED_DATASET_SOURCES = {"path", "url", "manual"}

_STORE_LOCK = Lock()
_STORE_PATH = Path(__file__).resolve().parents[2] / "logs" / "training_jobs.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_store_parent() -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_local_jobs() -> list[dict[str, Any]]:
    if not _STORE_PATH.exists():
        return []

    try:
        with _STORE_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if isinstance(payload, list):
            return payload
    except Exception:
        return []

    return []


def _save_local_jobs(jobs: list[dict[str, Any]]) -> None:
    _ensure_store_parent()
    with _STORE_PATH.open("w", encoding="utf-8") as file:
        json.dump(jobs, file, ensure_ascii=True, indent=2)


def normalize_training_payload(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    payload = payload or {}
    errors: list[str] = []

    model_name = (payload.get("model_name") or "").strip()
    if not model_name:
        errors.append("model_name is required")

    task_type = (payload.get("task_type") or "classification").strip().lower()
    if task_type not in ALLOWED_TASK_TYPES:
        errors.append(f"task_type must be one of: {', '.join(sorted(ALLOWED_TASK_TYPES))}")

    dataset_source = (payload.get("dataset_source") or "path").strip().lower()
    if dataset_source not in ALLOWED_DATASET_SOURCES:
        errors.append(
            f"dataset_source must be one of: {', '.join(sorted(ALLOWED_DATASET_SOURCES))}"
        )

    dataset_value = (payload.get("dataset_value") or "").strip()
    if not dataset_value:
        errors.append("dataset_value is required")
    if dataset_source != "path":
        errors.append("Currently only dataset_source='path' is supported for automated training")

    base_model = (payload.get("base_model") or "").strip() or "yolov8n"

    try:
        epochs = int(payload.get("epochs", 10))
        if epochs < 1:
            raise ValueError
    except Exception:
        errors.append("epochs must be an integer >= 1")
        epochs = 10

    try:
        batch_size = int(payload.get("batch_size", 16))
        if batch_size < 1:
            raise ValueError
    except Exception:
        errors.append("batch_size must be an integer >= 1")
        batch_size = 16

    try:
        image_size = int(payload.get("image_size", 640))
        if image_size < 64:
            raise ValueError
    except Exception:
        errors.append("image_size must be an integer >= 64")
        image_size = 640

    try:
        learning_rate = float(payload.get("learning_rate", 0.001))
        if learning_rate <= 0:
            raise ValueError
    except Exception:
        errors.append("learning_rate must be a number > 0")
        learning_rate = 0.001

    try:
        validation_split = float(payload.get("validation_split", 0.2))
        if not 0 < validation_split < 1:
            raise ValueError
    except Exception:
        errors.append("validation_split must be a number between 0 and 1")
        validation_split = 0.2

    try:
        quality_threshold = float(payload.get("quality_threshold", 0.60))
        if not 0 <= quality_threshold <= 1:
            raise ValueError
    except Exception:
        errors.append("quality_threshold must be a number between 0 and 1")
        quality_threshold = 0.60

    auto_deploy = bool(payload.get("auto_deploy", False))
    hf_space_slug = (payload.get("hf_space_slug") or "").strip()
    notes = (payload.get("notes") or "").strip()

    if errors:
        return None, errors

    normalized = {
        "model_name": model_name,
        "task_type": task_type,
        "base_model": base_model,
        "dataset_source": dataset_source,
        "dataset_value": dataset_value,
        "epochs": epochs,
        "batch_size": batch_size,
        "image_size": image_size,
        "learning_rate": learning_rate,
        "validation_split": validation_split,
        "quality_threshold": quality_threshold,
        "auto_deploy": auto_deploy,
        "hf_space_slug": hf_space_slug,
        "notes": notes,
    }
    return normalized, []


def create_training_job(user_id: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    now = _utc_now_iso()
    job = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "model_name": payload["model_name"],
        "task_type": payload["task_type"],
        "base_model": payload["base_model"],
        "dataset_source": payload["dataset_source"],
        "dataset_value": payload["dataset_value"],
        "config_json": {
            "epochs": payload["epochs"],
            "batch_size": payload["batch_size"],
            "image_size": payload["image_size"],
            "learning_rate": payload["learning_rate"],
            "validation_split": payload["validation_split"],
            "quality_threshold": payload["quality_threshold"],
        },
        "auto_deploy": payload["auto_deploy"],
        "hf_space_slug": payload["hf_space_slug"],
        "notes": payload["notes"],
        "status": "queued",
        "status_message": "Job accepted. Waiting for worker.",
        "artifact_path": None,
        "metrics_json": None,
        "best_metric": None,
        "quality_gate_passed": None,
        "model_id": None,
        "hf_space_url": None,
        "logs": [],
        "created_at": now,
        "updated_at": now,
    }

    try:
        supabase = get_supabase_client()
        response = supabase.table("training_jobs").insert(job).execute()
        inserted = (response.data or [None])[0]
        if inserted:
            return inserted, "supabase"
    except Exception:
        pass

    with _STORE_LOCK:
        jobs = _load_local_jobs()
        jobs.append(job)
        _save_local_jobs(jobs)

    return job, "local"


def list_training_jobs(user_id: str) -> tuple[list[dict[str, Any]], str]:
    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("training_jobs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or [], "supabase"
    except Exception:
        pass

    with _STORE_LOCK:
        jobs = [job for job in _load_local_jobs() if job.get("user_id") == user_id]

    jobs.sort(key=lambda row: row.get("created_at", ""), reverse=True)
    return jobs, "local"


def get_training_job(user_id: str, job_id: str) -> tuple[dict[str, Any] | None, str]:
    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("training_jobs")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        row = (response.data or [None])[0]
        if row:
            return row, "supabase"
    except Exception:
        pass

    with _STORE_LOCK:
        for job in _load_local_jobs():
            if job.get("user_id") == user_id and job.get("id") == job_id:
                return job, "local"

    return None, "local"


def get_training_job_any(job_id: str) -> tuple[dict[str, Any] | None, str]:
    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("training_jobs")
            .select("*")
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        row = (response.data or [None])[0]
        if row:
            return row, "supabase"
    except Exception:
        pass

    with _STORE_LOCK:
        for job in _load_local_jobs():
            if job.get("id") == job_id:
                return job, "local"

    return None, "local"


def update_training_job(
    job_id: str,
    updates: dict[str, Any],
    user_id: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    if not updates:
        return get_training_job_any(job_id)

    update_payload = {**updates, "updated_at": _utc_now_iso()}

    try:
        supabase = get_supabase_client()
        query = supabase.table("training_jobs").update(update_payload).eq("id", job_id)
        if user_id:
            query = query.eq("user_id", user_id)
        response = query.execute()
        rows = response.data or []
        if rows:
            return rows[0], "supabase"

        # Some setups return empty data; fetch explicitly.
        if user_id:
            return get_training_job(user_id, job_id)
        return get_training_job_any(job_id)
    except Exception:
        pass

    with _STORE_LOCK:
        jobs = _load_local_jobs()
        updated = None
        for idx, job in enumerate(jobs):
            if job.get("id") != job_id:
                continue
            if user_id and job.get("user_id") != user_id:
                continue
            merged = {**job, **update_payload}
            jobs[idx] = merged
            updated = merged
            break

        if updated is not None:
            _save_local_jobs(jobs)
            return updated, "local"

    return None, "local"


def append_training_job_log(
    job_id: str,
    message: str,
    user_id: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    if user_id:
        job, backend = get_training_job(user_id, job_id)
    else:
        job, backend = get_training_job_any(job_id)

    if not job:
        return None, backend

    logs = list(job.get("logs") or [])
    logs.append({"ts": _utc_now_iso(), "message": str(message)})
    return update_training_job(job_id, {"logs": logs}, user_id=user_id)
