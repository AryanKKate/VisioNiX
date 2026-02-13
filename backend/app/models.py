import torch
from ultralytics import YOLO
from transformers import BlipProcessor, BlipForConditionalGeneration
from transformers import CLIPProcessor, CLIPModel
from doctr.models import ocr_predictor

import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import urllib.request
import os



device = "cuda" if torch.cuda.is_available() else "cpu"

yolo_model = YOLO("yolov8n.pt")

blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
blip_model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-base"
).to(device)

ocr_model = ocr_predictor("db_resnet50","crnn_vgg16_bn",pretrained=True)


clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

clip_model = CLIPModel.from_pretrained(
    "openai/clip-vit-base-patch32"
).to(device)

clip_model.eval()

label_file = "categories_places365.txt"
if not os.path.exists(label_file):
    urllib.request.urlretrieve(
        "https://raw.githubusercontent.com/CSAILVision/places365/master/categories_places365.txt",
        label_file
    )

scene_labels_list = []
with open(label_file) as class_file:
    for line in class_file:
        scene_labels_list.append(line.strip().split(" ")[0][3:])

# ---------- Load Model ----------
weight_file = "resnet18_places365.pth.tar"
if not os.path.exists(weight_file):
    urllib.request.urlretrieve(
        "http://places2.csail.mit.edu/models_places365/resnet18_places365.pth.tar",
        weight_file
    )

scene_model = models.resnet18(num_classes=365)
checkpoint = torch.load(weight_file, map_location=device)
state_dict = {k.replace("module.", ""): v for k, v in checkpoint["state_dict"].items()}
scene_model.load_state_dict(state_dict)
scene_model = scene_model.to(device)
scene_model.eval()

# ---------- Transform ----------
scene_transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

def classify_scene(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
        input_tensor = scene_transform(img).unsqueeze(0).to(device)

        with torch.no_grad():
            logits = scene_model(input_tensor)
            probs = torch.softmax(logits, 1).squeeze()
            topk = torch.topk(probs, 3)

        indices = topk.indices.tolist()
        return [scene_labels_list[i] for i in indices]

    except Exception as e:
        return [f"Scene classification failed: {e}"]


