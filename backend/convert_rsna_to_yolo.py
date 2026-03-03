import os
import pandas as pd
import pydicom
import cv2
import numpy as np
from sklearn.model_selection import train_test_split
from tqdm import tqdm

BASE_DIR = "data/rsna"
DICOM_DIR = os.path.join(BASE_DIR, "dicom", "stage_2_train_images")
CSV_PATH = os.path.join(BASE_DIR, "stage_2_train_labels.csv")

OUTPUT_IMAGES = os.path.join(BASE_DIR, "images")
OUTPUT_LABELS = os.path.join(BASE_DIR, "labels")

print("Checking paths...")
print("DICOM_DIR:", DICOM_DIR)
print("CSV_PATH:", CSV_PATH)

if not os.path.exists(DICOM_DIR):
    print("❌ DICOM folder not found!")
    exit()

if not os.path.exists(CSV_PATH):
    print("❌ CSV file not found!")
    exit()

# Create output folders
for split in ["train", "val"]:
    os.makedirs(os.path.join(OUTPUT_IMAGES, split), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_LABELS, split), exist_ok=True)

df = pd.read_csv(CSV_PATH)
print("CSV loaded. Total rows:", len(df))

patient_ids = df["patientId"].unique()
print("Unique patients:", len(patient_ids))

train_ids, val_ids = train_test_split(patient_ids, test_size=0.2, random_state=42)

def convert_patient(patient_id, split):
    dicom_path = os.path.join(DICOM_DIR, f"{patient_id}.dcm")
    if not os.path.exists(dicom_path):
        return

    ds = pydicom.dcmread(dicom_path)
    img = ds.pixel_array

    img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
    img = img.astype(np.uint8)

    h, w = img.shape

    img_path = os.path.join(OUTPUT_IMAGES, split, f"{patient_id}.jpg")
    cv2.imwrite(img_path, img)

    label_path = os.path.join(OUTPUT_LABELS, split, f"{patient_id}.txt")
    patient_data = df[df["patientId"] == patient_id]

    with open(label_path, "w") as f:
        for _, row in patient_data.iterrows():
            if row["Target"] == 1:
                x, y, width, height = row["x"], row["y"], row["width"], row["height"]

                x_center = (x + width / 2) / w
                y_center = (y + height / 2) / h
                width /= w
                height /= h

                f.write(f"0 {x_center} {y_center} {width} {height}\n")

print("Processing Train...")
for pid in tqdm(train_ids):
    convert_patient(pid, "train")

print("Processing Val...")
for pid in tqdm(val_ids):
    convert_patient(pid, "val")

print("Conversion Complete ✅")