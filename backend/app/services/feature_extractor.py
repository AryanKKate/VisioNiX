import os
import base64
import requests
from datetime import datetime, timezone

import numpy as np
import torch
from doctr.io import DocumentFile
from PIL import Image

from app.models import (
    blip_model,
    blip_processor,
    classify_scene,
    clip_model,
    clip_processor,
    ocr_model,
    yolo_model,
)

EMBEDDINGS_DIR = "embeddings"
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"


# ==============================
# EXISTING LOCAL EXTRACTION
# ==============================
def extract_features(image_path):
    print("🎶🎶🎶 Local")
    image = Image.open(image_path).convert("RGB")

    # BLIP Caption
    inputs = blip_processor(image, return_tensors="pt").to(device)
    out = blip_model.generate(**inputs)
    caption = blip_processor.decode(out[0], skip_special_tokens=True)

    # YOLO Objects
    results = yolo_model(image)
    objects = [
        yolo_model.names[int(box.cls)]
        for box in results[0].boxes
    ]

    # OCR
    doc = DocumentFile.from_images(image_path)
    result = ocr_model(doc)

    ocr_text = ""
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                ocr_text += " ".join([word.value for word in line.words]) + " "

    # Scene
    scene = classify_scene(image_path)

    # Color
    img_array = np.array(image)
    mean_color = img_array.mean(axis=(0, 1)).tolist()

    # Texture
    texture = img_array.var(axis=(0, 1)).tolist()

    # CLIP Embedding
    clip_inputs = clip_processor(images=image, return_tensors="pt")
    clip_inputs = {k: v.to(device) for k, v in clip_inputs.items()}

    with torch.no_grad():
        clip_vector = clip_model.get_image_features(
            pixel_values=clip_inputs["pixel_values"]
        )

    clip_vector = torch.nn.functional.normalize(
        clip_vector, p=2, dim=-1
    )
    clip_vector = clip_vector.detach().cpu().numpy().flatten()

    return _finalize_output(
        image_path,
        caption,
        objects,
        ocr_text,
        scene,
        mean_color,
        texture,
        clip_vector
    )


# ==============================
# NEW: HF REMOTE EXTRACTION
# ==============================
from gradio_client import Client, handle_file

def _extract_from_hf(image_path, model_url):

    print("😊😊 Hugging Face")

    try:
        client = Client(model_url)

        result = client.predict(
            handle_file(image_path),
            api_name="/predict"
        )

    except Exception as e:
        raise Exception(f"HF Gradio Client Error: {str(e)}")

    # ----------------------------------------
    # HF RETURNS ONLY YOLO DETECTIONS
    # ----------------------------------------
    detections = result.get("detections", [])

    # Extract class_ids
    class_ids = [d["class_id"] for d in detections]

    # Convert class_ids -> names using local YOLO model
    objects = [yolo_model.names[int(cid)] for cid in class_ids]

    # ----------------------------------------
    # RUN ALL OTHER FEATURES LOCALLY
    # ----------------------------------------
    image = Image.open(image_path).convert("RGB")

    # BLIP Caption
    inputs = blip_processor(image, return_tensors="pt").to(device)
    out = blip_model.generate(**inputs)
    caption = blip_processor.decode(out[0], skip_special_tokens=True)

    # OCR
    doc = DocumentFile.from_images(image_path)
    ocr_result = ocr_model(doc)

    ocr_text = ""
    for page in ocr_result.pages:
        for block in page.blocks:
            for line in block.lines:
                ocr_text += " ".join([word.value for word in line.words]) + " "

    # Scene
    scene = classify_scene(image_path)

    # Color
    img_array = np.array(image)
    mean_color = img_array.mean(axis=(0, 1)).tolist()

    # Texture
    texture = img_array.var(axis=(0, 1)).tolist()

    # CLIP Embedding (LOCAL)
    clip_inputs = clip_processor(images=image, return_tensors="pt")
    clip_inputs = {k: v.to(device) for k, v in clip_inputs.items()}

    with torch.no_grad():
        clip_vector = clip_model.get_image_features(
            pixel_values=clip_inputs["pixel_values"]
        )

    clip_vector = torch.nn.functional.normalize(
        clip_vector, p=2, dim=-1
    )
    clip_vector = clip_vector.detach().cpu().numpy().flatten()

    # ----------------------------------------
    # FINAL OUTPUT
    # ----------------------------------------
    return _finalize_output(
        image_path,
        caption,
        objects,
        ocr_text,
        scene,
        mean_color,
        texture,
        clip_vector
    )


# ==============================
# NEW: SMART ROUTER FUNCTION
# ==============================
def extract_features_with_model(image_path, model=None):
    """Use HF extraction when a remote model URL is available."""
    if not model:
        return extract_features(image_path)

    if isinstance(model, str):
        model_url = model.strip()
    elif isinstance(model, dict):
        model_url = (
            model.get("hf_space_url")
            or model.get("hf_url")
            or model.get("endpoint_url")
            or ""
        ).strip()
    else:
        raise ValueError("Invalid model payload; expected dict or URL string.")

    if not model_url:
        raise ValueError("Selected model does not have a valid hf_space_url.")

    return _extract_from_hf(image_path, model_url)


# ==============================
# SHARED FINALIZER
# ==============================
def _finalize_output(
    image_path,
    caption,
    objects,
    ocr_text,
    scene,
    mean_color,
    texture,
    clip_vector
):

    image_name = os.path.basename(image_path)
    base_name = os.path.splitext(image_name)[0]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    embedding_filename = f"{base_name}_{timestamp}.npy"
    embedding_path = os.path.join(EMBEDDINGS_DIR, embedding_filename)

    np.save(embedding_path, clip_vector)

    return {
        "image_name": image_name,
        "caption": caption,
        "objects": objects,
        "ocr_text": ocr_text,
        "scene_labels": scene,
        "color_features": mean_color,
        "texture_features": texture,
        "clip_embedding_file": embedding_filename,
        "clip_embedding_path": embedding_path,
        "extracted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "embed": clip_vector.tolist()
    }
