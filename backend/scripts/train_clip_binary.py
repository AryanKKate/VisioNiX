import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import CLIPProcessor, CLIPModel
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from tqdm import tqdm
import pydicom
import numpy as np
from PIL import Image

device = "cuda" if torch.cuda.is_available() else "cpu"

# ------------------------
# Dataset (DICOM version)
# ------------------------

class RSNABinaryDataset(Dataset):
    def __init__(self, root_dir, processor):
        self.processor = processor
        self.samples = []

        for label_name in ["normal", "pneumonia"]:
            class_dir = os.path.join(root_dir, label_name)
            for file in os.listdir(class_dir):
                if file.endswith(".dcm"):
                    self.samples.append((
                        os.path.join(class_dir, file),
                        0 if label_name == "normal" else 1
                    ))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]

        ds = pydicom.dcmread(img_path)
        img = ds.pixel_array.astype(np.float32)

        img = (np.maximum(img, 0) / img.max()) * 255.0
        img = np.uint8(img)

        image = Image.fromarray(img).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        pixel_values = inputs["pixel_values"].squeeze(0)

        return pixel_values, torch.tensor(label, dtype=torch.long)


# ------------------------
# Load CLIP
# ------------------------

clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_model = clip_model.to(device)

# Freeze everything first
for param in clip_model.parameters():
    param.requires_grad = False

# 🔥 Unfreeze last 2 vision transformer layers
for name, param in clip_model.named_parameters():
    if "vision_model.encoder.layers.10" in name or \
       "vision_model.encoder.layers.11" in name:
        param.requires_grad = True

processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

classifier = nn.Linear(clip_model.config.projection_dim, 2).to(device)

# ------------------------
# Dataset Paths
# ------------------------

train_dataset = RSNABinaryDataset("data/rsna_binary/train", processor)
val_dataset = RSNABinaryDataset("data/rsna_binary/val", processor)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=0)
val_loader = DataLoader(val_dataset, batch_size=32, num_workers=0)

# ------------------------
# Handle Class Imbalance
# ------------------------

class_counts = torch.tensor([16537, 4810], dtype=torch.float)
weights = 1.0 / class_counts
weights = weights / weights.sum()

criterion = nn.CrossEntropyLoss(weight=weights.to(device))

# 🔥 Optimizer now includes CLIP unfrozen params + classifier
optimizer = torch.optim.Adam(
    filter(lambda p: p.requires_grad, list(clip_model.parameters()) + list(classifier.parameters())),
    lr=2e-5
)

# ------------------------
# Training Loop
# ------------------------

epochs = 5
best_val_acc = 0

for epoch in range(epochs):

    clip_model.train()
    classifier.train()

    total_loss = 0
    all_train_preds = []
    all_train_labels = []

    for images, labels in tqdm(train_loader):
        images = images.to(device)
        labels = labels.to(device)

        image_features = clip_model.get_image_features(pixel_values=images)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        outputs = classifier(image_features)
        loss = criterion(outputs, labels)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        preds = torch.argmax(outputs, dim=1)
        all_train_preds.extend(preds.cpu().numpy())
        all_train_labels.extend(labels.cpu().numpy())

    train_acc = accuracy_score(all_train_labels, all_train_preds)

    print(f"\nEpoch {epoch+1}")
    print(f"Train Loss: {total_loss/len(train_loader):.4f}")
    print(f"Train Accuracy: {train_acc:.4f}")

    # -------- Validation --------

    clip_model.eval()
    classifier.eval()

    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            labels = labels.to(device)

            image_features = clip_model.get_image_features(pixel_values=images)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            outputs = classifier(image_features)
            probs = torch.softmax(outputs, dim=1)[:, 1]

            preds = torch.argmax(outputs, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    val_acc = accuracy_score(all_labels, all_preds)
    roc_auc = roc_auc_score(all_labels, all_probs)

    print(f"Validation Accuracy: {val_acc:.4f}")
    print(f"ROC-AUC: {roc_auc:.4f}")

    # 🔥 Save best model
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save({
            "clip": clip_model.state_dict(),
            "classifier": classifier.state_dict()
        }, "models/clip_binary_best.pth")
        print("✅ Best model saved")

# ------------------------
# Final Evaluation Report
# ------------------------

print("\nClassification Report:")
print(classification_report(all_labels, all_preds))

print("Confusion Matrix:")
print(confusion_matrix(all_labels, all_preds))

print("\nTraining complete.")