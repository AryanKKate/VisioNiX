import torch
import torch.nn as nn
from transformers import CLIPModel, CLIPProcessor
from ultralytics import YOLO
from PIL import Image
import os

device = "cuda" if torch.cuda.is_available() else "cpu"

# =========================
# Load CLIP Architecture
# =========================

clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_model = clip_model.to(device)

classifier = nn.Linear(clip_model.config.projection_dim, 2).to(device)

# Load saved weights
checkpoint = torch.load("models/clip_binary_best.pth", map_location=device)
clip_model.load_state_dict(checkpoint["clip"])
classifier.load_state_dict(checkpoint["classifier"])

clip_model.eval()
classifier.eval()

processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# =========================
# Load YOLO
# =========================

yolo_model = YOLO("runs/detect/train11/weights/best.pt")

# =========================
# CLIP Prediction
# =========================

def clip_predict(image_path):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(device)

    with torch.no_grad():
        image_features = clip_model.get_image_features(pixel_values=pixel_values)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        outputs = classifier(image_features)
        probs = torch.softmax(outputs, dim=1)

        confidence, predicted = torch.max(probs, 1)

    label = "pneumonia" if predicted.item() == 1 else "normal"

    return {
        "label": label,
        "confidence": float(confidence.item())
    }

# =========================
# Full Medical Pipeline
# =========================

def medical_analysis(image_path):
    classification = clip_predict(image_path)

    detections = None

    if classification["label"] == "pneumonia":
        results = yolo_model(image_path, imgsz=768, conf=0.15)

        if results[0].boxes is not None:
            detections = results[0].boxes.xyxy.cpu().numpy().tolist()
        else:
            detections = []

    return {
        "classification": classification,
        "detections": detections
    }

# =========================
# Test Block
# =========================

if __name__ == "__main__":
    result = medical_analysis("test_xray.jpg")
    print(result)