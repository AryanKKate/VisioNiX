import csv
import traceback
from pathlib import Path
from threading import Lock, Thread
from typing import Any

from app.services.db import upsert_user_model
from app.services.hf_deploy import deploy_to_hf_space
from app.services.training_jobs import (
    append_training_job_log,
    get_training_job,
    update_training_job,
)


_RUNNING_LOCK = Lock()
_RUNNING_JOB_IDS: set[str] = set()


def _as_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _resolve_backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(dataset_path: str) -> Path:
    path = Path(dataset_path)
    if path.is_absolute():
        return path
    return (_resolve_backend_root() / path).resolve()


def _resolve_base_model(base_model: str, task_type: str) -> str:
    value = (base_model or "").strip()
    if value.endswith(".pt") or "/" in value or "\\" in value:
        return value

    defaults = {
        "classification": "yolov8n-cls.pt",
        "detection": "yolov8n.pt",
        "segmentation": "yolov8n-seg.pt",
    }
    if not value:
        return defaults.get(task_type, "yolov8n.pt")

    if value.endswith("-cls") or value.endswith("-seg"):
        return f"{value}.pt"

    if task_type == "classification" and "-cls" not in value:
        return f"{value}-cls.pt"
    if task_type == "segmentation" and "-seg" not in value:
        return f"{value}-seg.pt"

    return f"{value}.pt"


def _append_log(job_id: str, user_id: str, message: str) -> None:
    append_training_job_log(job_id=job_id, user_id=user_id, message=message)


def _set_state(job_id: str, user_id: str, status: str, message: str, **extra) -> None:
    payload = {
        "status": status,
        "status_message": message,
        **extra,
    }
    update_training_job(job_id=job_id, user_id=user_id, updates=payload)
    _append_log(job_id, user_id, f"[{status}] {message}")


def _parse_metrics_csv(results_csv_path: Path) -> dict[str, Any]:
    if not results_csv_path.exists():
        return {}

    with results_csv_path.open("r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        return {}

    latest = rows[-1]
    parsed = {}
    for key, value in latest.items():
        parsed[key] = _as_float(value, value)
    return parsed


def _select_quality_metric(task_type: str, metrics: dict[str, Any]) -> tuple[str | None, float | None]:
    candidates_by_task = {
        "classification": [
            "metrics/accuracy_top1",
            "metrics/accuracy_top5",
        ],
        "detection": [
            "metrics/mAP50(B)",
            "metrics/recall(B)",
        ],
        "segmentation": [
            "metrics/mAP50(M)",
            "metrics/mAP50(B)",
        ],
    }

    for key in candidates_by_task.get(task_type, []):
        if key in metrics and isinstance(metrics[key], (int, float)):
            return key, float(metrics[key])

    for key, value in metrics.items():
        if isinstance(value, (int, float)) and key.startswith("metrics/"):
            return key, float(value)

    return None, None


def _run_ultralytics_training(job: dict[str, Any]) -> tuple[Path, dict[str, Any], str | None, float | None]:
    from ultralytics import YOLO

    user_id = str(job["user_id"])
    job_id = str(job["id"])
    task_type = str(job.get("task_type") or "classification")
    dataset_source = str(job.get("dataset_source") or "path")

    if dataset_source != "path":
        raise ValueError("Only dataset_source='path' is currently supported by automated training")

    dataset_path = _resolve_path(str(job.get("dataset_value") or ""))
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset path does not exist: {dataset_path}")

    config = job.get("config_json") or {}
    epochs = int(config.get("epochs", 10))
    batch_size = int(config.get("batch_size", 16))
    image_size = int(config.get("image_size", 640))
    lr = float(config.get("learning_rate", 0.001))

    base_model = _resolve_base_model(str(job.get("base_model") or ""), task_type)

    project_dir = _resolve_backend_root() / "runs" / "finetune_jobs"
    run_name = f"job_{job_id}"

    _append_log(job_id, user_id, f"Loading base model: {base_model}")
    model = YOLO(base_model)

    _append_log(job_id, user_id, f"Training started on dataset: {dataset_path}")
    model.train(
        data=str(dataset_path),
        epochs=epochs,
        batch=batch_size,
        imgsz=image_size,
        lr0=lr,
        project=str(project_dir),
        name=run_name,
        exist_ok=True,
        verbose=False,
    )

    save_dir = Path(getattr(model.trainer, "save_dir", project_dir / run_name))
    weights_dir = save_dir / "weights"

    best_candidates = [weights_dir / "best.pt", weights_dir / "last.pt"]
    best_artifact = None
    for candidate in best_candidates:
        if candidate.exists():
            best_artifact = candidate
            break

    if best_artifact is None:
        raise FileNotFoundError(f"Training finished but no weight file found in: {weights_dir}")

    metrics = _parse_metrics_csv(save_dir / "results.csv")
    metric_key, best_metric = _select_quality_metric(task_type=task_type, metrics=metrics)

    return best_artifact, metrics, metric_key, best_metric


def _deploy_and_register(job: dict[str, Any], model_artifact_path: str) -> dict[str, Any]:
    deployment = deploy_to_hf_space(
        model_artifact_path=model_artifact_path,
        model_name=str(job.get("model_name") or "VisioNiX Model"),
        task_type=str(job.get("task_type") or "classification"),
        hf_space_slug=str(job.get("hf_space_slug") or "") or None,
    )

    model_row = upsert_user_model(
        user_id=str(job["user_id"]),
        name=str(job.get("model_name") or "VisioNiX Model"),
        hf_space_url=deployment.get("hf_space_url"),
        task_type=str(job.get("task_type") or "classification"),
        status="deployed",
    )

    model_id = model_row.get("id") if isinstance(model_row, dict) else None

    return {
        "deployment": deployment,
        "model": model_row,
        "model_id": model_id,
    }


def _run_job(job: dict[str, Any]) -> None:
    job_id = str(job["id"])
    user_id = str(job["user_id"])

    try:
        _set_state(job_id, user_id, "running", "Fine-tuning started")

        artifact_path, metrics, metric_key, best_metric = _run_ultralytics_training(job)

        _set_state(
            job_id,
            user_id,
            "trained",
            "Training completed",
            artifact_path=str(artifact_path),
            metrics_json=metrics,
            best_metric=best_metric,
        )

        threshold = _as_float((job.get("config_json") or {}).get("quality_threshold", 0.60), 0.60)
        quality_passed = best_metric is None or best_metric >= threshold

        _set_state(
            job_id,
            user_id,
            "quality_check",
            "Evaluating model quality gate",
            quality_gate_passed=quality_passed,
        )

        if not quality_passed:
            _set_state(
                job_id,
                user_id,
                "rejected",
                f"Model did not meet quality threshold ({metric_key}={best_metric:.4f} < {threshold:.4f})",
            )
            return

        _append_log(job_id, user_id, "Quality gate passed")

        model_row = upsert_user_model(
            user_id=user_id,
            name=str(job.get("model_name") or "VisioNiX Model"),
            hf_space_url=None,
            task_type=str(job.get("task_type") or "classification"),
            status="trained",
        )
        model_id = model_row.get("id") if isinstance(model_row, dict) else None

        _set_state(
            job_id,
            user_id,
            "ready_for_deploy" if not job.get("auto_deploy") else "deploying",
            "Model is ready for deployment" if not job.get("auto_deploy") else "Deploying to Hugging Face",
            model_id=model_id,
        )

        if job.get("auto_deploy"):
            deploy_result = _deploy_and_register(job, str(artifact_path))
            deployment = deploy_result.get("deployment") or {}
            _set_state(
                job_id,
                user_id,
                "completed",
                "Training and Hugging Face deployment completed",
                hf_space_url=deployment.get("hf_space_url"),
                model_id=deploy_result.get("model_id") or model_id,
            )
        else:
            _set_state(
                job_id,
                user_id,
                "completed",
                "Training completed. Trigger deployment when ready.",
                model_id=model_id,
            )

    except Exception as exc:
        traceback_text = traceback.format_exc(limit=20)
        _set_state(
            job_id,
            user_id,
            "failed",
            f"Training pipeline failed: {exc}",
            error=traceback_text,
        )

    finally:
        with _RUNNING_LOCK:
            _RUNNING_JOB_IDS.discard(job_id)


def enqueue_training_job(job: dict[str, Any]) -> bool:
    job_id = str(job["id"])
    with _RUNNING_LOCK:
        if job_id in _RUNNING_JOB_IDS:
            return False
        _RUNNING_JOB_IDS.add(job_id)

    worker = Thread(target=_run_job, args=(job,), daemon=True, name=f"training-{job_id[:8]}")
    worker.start()
    return True


def deploy_training_job(user_id: str, job_id: str) -> dict[str, Any]:
    job, _ = get_training_job(user_id=user_id, job_id=job_id)
    if not job:
        raise ValueError("job not found")

    if str(job.get("status")) in {"queued", "running", "deploying"}:
        raise ValueError("job is still in progress")

    artifact_path = (job.get("artifact_path") or "").strip()
    if not artifact_path:
        raise ValueError("job does not have artifact_path yet")

    _set_state(job_id, user_id, "deploying", "Deploying to Hugging Face")
    deploy_result = _deploy_and_register(job, artifact_path)
    deployment = deploy_result.get("deployment") or {}

    updated_job, _ = update_training_job(
        job_id=job_id,
        user_id=user_id,
        updates={
            "status": "completed",
            "status_message": "Deployment completed",
            "hf_space_url": deployment.get("hf_space_url"),
            "model_id": deploy_result.get("model_id") or job.get("model_id"),
        },
    )

    return {
        "job": updated_job,
        "deployment": deployment,
        "model": deploy_result.get("model"),
    }
