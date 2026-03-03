import os
import pandas as pd
from PIL import Image

csv_path = "data/rsna/stage_2_train_labels.csv"
image_dir = "data/rsna/images"
label_dir = "data/rsna/labels"

os.makedirs(label_dir, exist_ok=True)

df = pd.read_csv(csv_path)

# Group by patientId
grouped = df.groupby("patientId")

for patient_id, group in grouped:
    img_path = os.path.join(image_dir, patient_id + ".jpg")

    if not os.path.exists(img_path):
        continue

    img = Image.open(img_path)
    img_w, img_h = img.size

    label_file = os.path.join(label_dir, patient_id + ".txt")

    with open(label_file, "w") as f:
        for _, row in group.iterrows():
            if row["Target"] == 1:
                x = row["x"]
                y = row["y"]
                w = row["width"]
                h = row["height"]

                x_center = (x + w / 2) / img_w
                y_center = (y + h / 2) / img_h
                w_norm = w / img_w
                h_norm = h / img_h

                f.write(f"0 {x_center} {y_center} {w_norm} {h_norm}\n")
