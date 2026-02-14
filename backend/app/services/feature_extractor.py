import numpy as np
from PIL import Image
from app.models import yolo_model, blip_processor, blip_model, clip_processor, clip_model, ocr_model, classify_scene
from doctr.io import DocumentFile
import torch
import os
import numpy as np
from datetime import datetime

EMBEDDINGS_DIR = "embeddings"
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)


device = "cuda" if torch.cuda.is_available() else "cpu"

def extract_features(image_path):
    image = Image.open(image_path).convert("RGB")

    # ---------- BLIP Caption ----------
    inputs = blip_processor(image, return_tensors="pt").to(device)
    out = blip_model.generate(**inputs)
    caption = blip_processor.decode(out[0], skip_special_tokens=True)

    # ---------- YOLO Objects ----------
    results = yolo_model(image)
    objects = [
        yolo_model.names[int(box.cls)]
        for box in results[0].boxes
    ]

    # ---------- OCR ----------
    doc = DocumentFile.from_images(image_path)
    result = ocr_model(doc)

    ocr_text = ""
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                ocr_text += " ".join([word.value for word in line.words]) + " "

    # ---------- Scene Classification ----------
    scene = classify_scene(image_path)


    # ---------- Color Features ----------
    img_array = np.array(image)
    mean_color = img_array.mean(axis=(0, 1)).tolist()

    # ---------- Texture Features (simple example: variance) ----------
    texture = img_array.var(axis=(0, 1)).tolist()

    # ---------- CLIP Embedding ----------
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

    # ---------- Save Embedding ----------
    image_name = os.path.basename(image_path)
    base_name = os.path.splitext(image_name)[0]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    embedding_filename = f"{base_name}_{timestamp}.npy"
    embedding_path = os.path.join(EMBEDDINGS_DIR, embedding_filename)

    np.save(embedding_path, clip_vector)

    # ---------- Return JSON ----------
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
        "embedding": clip_vector.tolist()
    }







