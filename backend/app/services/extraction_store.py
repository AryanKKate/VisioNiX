from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
import uuid

_EXTRACTIONS: list[dict] = []
_EXTRACTION_LOCK = Lock()


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text_list(values) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _normalize_numeric_list(values) -> list[float]:
    if not isinstance(values, list):
        return []

    cleaned: list[float] = []
    for value in values:
        try:
            cleaned.append(float(value))
        except (TypeError, ValueError):
            continue
    return cleaned


def add_extraction_record(
    *,
    features: dict,
    image_name: str,
    image_path: str | None = None,
    source: str = "unknown",
) -> dict:
    record = {
        "id": str(uuid.uuid4()),
        "image_name": image_name,
        "caption": str(features.get("caption", "")).strip(),
        "objects": _normalize_text_list(features.get("objects")),
        "ocr_text": str(features.get("ocr_text", "")).strip(),
        "scene_labels": _normalize_text_list(features.get("scene_labels")),
        "color_features": _normalize_numeric_list(features.get("color_features")),
        "texture_features": _normalize_numeric_list(features.get("texture_features")),
        "clip_embedding_file": str(features.get("clip_embedding_file", "")).strip(),
        "clip_embedding_path": str(features.get("clip_embedding_path", "")).strip(),
        "timestamp": str(features.get("extracted_at") or _now_utc_iso()),
        "source": source,
    }

    if image_path:
        record["image_path"] = image_path

    with _EXTRACTION_LOCK:
        _EXTRACTIONS.insert(0, record)

    return deepcopy(record)


def list_extraction_records() -> list[dict]:
    with _EXTRACTION_LOCK:
        return deepcopy(_EXTRACTIONS)


def delete_extraction_record(extraction_id: str) -> bool:
    with _EXTRACTION_LOCK:
        for idx, record in enumerate(_EXTRACTIONS):
            if record.get("id") == extraction_id:
                del _EXTRACTIONS[idx]
                return True
    return False
