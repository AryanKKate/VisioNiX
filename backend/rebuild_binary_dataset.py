import os
import shutil
import pandas as pd
from sklearn.model_selection import train_test_split

# Paths
BASE_PATH = "data/rsna"
DICOM_PATH = os.path.join(BASE_PATH, "dicom/stage_2_train_images")
CSV_PATH = os.path.join(BASE_PATH, "stage_2_train_labels.csv")

OUTPUT_PATH = "data/rsna_binary"

# Create output folders
for split in ["train", "val"]:
    for cls in ["normal", "pneumonia"]:
        os.makedirs(os.path.join(OUTPUT_PATH, split, cls), exist_ok=True)

# Load CSV
df = pd.read_csv(CSV_PATH)

# Determine class per patient
patient_targets = df.groupby("patientId")["Target"].max().reset_index()

# Split into train/val
train_df, val_df = train_test_split(
    patient_targets,
    test_size=0.2,
    stratify=patient_targets["Target"],
    random_state=42
)

def copy_images(dataframe, split_name):
    for _, row in dataframe.iterrows():
        patient_id = row["patientId"]
        label = "pneumonia" if row["Target"] == 1 else "normal"

        src = os.path.join(DICOM_PATH, patient_id + ".dcm")
        dst = os.path.join(OUTPUT_PATH, split_name, label, patient_id + ".dcm")

        if os.path.exists(src):
            shutil.copy(src, dst)

# Copy files
copy_images(train_df, "train")
copy_images(val_df, "val")

print("Dataset rebuilt successfully!")
print("Train size:", len(train_df))
print("Val size:", len(val_df))