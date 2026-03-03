import os
import pydicom
import numpy as np
from PIL import Image
from tqdm import tqdm

dicom_dir = "data/rsna/dicom"
output_dir = "data/rsna/images"

os.makedirs(output_dir, exist_ok=True)

for file in tqdm(os.listdir(dicom_dir)):
    if file.endswith(".dcm"):
        path = os.path.join(dicom_dir, file)
        ds = pydicom.dcmread(path)
        img = ds.pixel_array

        # Normalize to 0-255
        img = img - np.min(img)
        img = img / np.max(img)
        img = (img * 255).astype(np.uint8)

        image = Image.fromarray(img)
        image = image.convert("RGB")

        image.save(os.path.join(output_dir, file.replace(".dcm", ".jpg")))
