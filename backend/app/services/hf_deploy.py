import os
import re
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from huggingface_hub import HfApi


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9-]+", "-", value.strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "model"


def _resolve_space_slug(model_name: str, requested_slug: str | None = None) -> str:
    if requested_slug:
        slug = requested_slug.strip()
        if "/" in slug:
            return slug
        owner = (os.getenv("HF_SPACE_OWNER") or os.getenv("HF_USERNAME_OR_ORG") or "").strip()
        if owner:
            return f"{owner}/{slug}"
        return slug

    owner = (os.getenv("HF_SPACE_OWNER") or os.getenv("HF_USERNAME_OR_ORG") or "").strip()
    if not owner:
        raise ValueError("HF_SPACE_OWNER or HF_USERNAME_OR_ORG env var is required when hf_space_slug is not provided")
    return f"{owner}/{_slugify(model_name)}"


def _space_app_template(model_name: str, task_type: str) -> str:
    safe_name = model_name.replace("\"", "'")
    safe_task = task_type.replace("\"", "'")
    return f'''import tempfile\nfrom pathlib import Path\n\nimport gradio as gr\nfrom ultralytics import YOLO\n\nMODEL_PATH = Path(__file__).parent / "model.pt"\nmodel = YOLO(str(MODEL_PATH))\n\n\ndef predict(image):\n    if image is None:\n        return {{"error": "No image provided", "detections": []}}\n\n    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:\n        image.save(tmp.name)\n        temp_path = tmp.name\n\n    try:\n        results = model(temp_path)\n        detections = []\n        boxes = getattr(results[0], "boxes", None)\n        if boxes is not None:\n            for box in boxes:\n                detections.append({{\n                    "class_id": int(box.cls.item()),\n                    "confidence": float(box.conf.item()),\n                    "xyxy": [float(x) for x in box.xyxy[0].tolist()],\n                }})\n        return {{"model": "{safe_name}", "task": "{safe_task}", "detections": detections}}\n    finally:\n        Path(temp_path).unlink(missing_ok=True)\n\n\ndemo = gr.Interface(\n    fn=predict,\n    inputs=gr.Image(type="pil", label="Upload image"),\n    outputs=gr.JSON(label="output"),\n    title="{safe_name}",\n    description="Automated deployment from VisioNiX",\n    allow_flagging="never",\n)\n\nif __name__ == "__main__":\n    demo.launch()\n'''


def deploy_to_hf_space(
    model_artifact_path: str,
    model_name: str,
    task_type: str,
    hf_space_slug: str | None = None,
) -> dict:
    token = (os.getenv("HF_TOKEN") or "").strip()
    if not token:
        raise ValueError("HF_TOKEN is required for Hugging Face deployment")

    artifact = Path(model_artifact_path).resolve()
    if not artifact.exists() or not artifact.is_file():
        raise FileNotFoundError(f"Model artifact not found: {artifact}")

    repo_id = _resolve_space_slug(model_name=model_name, requested_slug=hf_space_slug)

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="gradio", exist_ok=True)

    with TemporaryDirectory(prefix="visionix_space_") as temp_dir:
        bundle_dir = Path(temp_dir)

        shutil.copy2(artifact, bundle_dir / "model.pt")
        (bundle_dir / "app.py").write_text(_space_app_template(model_name, task_type), encoding="utf-8")
        (bundle_dir / "requirements.txt").write_text("gradio\nultralytics\npillow\n", encoding="utf-8")
        (bundle_dir / "README.md").write_text(
            f"# {model_name}\n\nAuto-deployed from VisioNiX training pipeline.\n",
            encoding="utf-8",
        )

        api.upload_folder(
            repo_id=repo_id,
            repo_type="space",
            folder_path=str(bundle_dir),
            commit_message=f"Deploy model {model_name} from VisioNiX",
        )

    return {
        "repo_id": repo_id,
        "space_url": f"https://huggingface.co/spaces/{repo_id}",
        "hf_space_url": f"https://{repo_id.replace('/', '-')}.hf.space",
    }
