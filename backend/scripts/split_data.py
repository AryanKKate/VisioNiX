import os
import random
import shutil

image_dir = "data/rsna/images"
label_dir = "data/rsna/labels"

train_img_dir = "data/rsna/train/images"
train_lbl_dir = "data/rsna/train/labels"
val_img_dir = "data/rsna/val/images"
val_lbl_dir = "data/rsna/val/labels"

os.makedirs(train_img_dir, exist_ok=True)
os.makedirs(train_lbl_dir, exist_ok=True)
os.makedirs(val_img_dir, exist_ok=True)
os.makedirs(val_lbl_dir, exist_ok=True)

images = os.listdir(image_dir)
random.shuffle(images)

split = int(0.8 * len(images))
train_images = images[:split]
val_images = images[split:]

for img in train_images:
    shutil.copy(os.path.join(image_dir, img), train_img_dir)
    lbl = img.replace(".jpg", ".txt")
    if os.path.exists(os.path.join(label_dir, lbl)):
        shutil.copy(os.path.join(label_dir, lbl), train_lbl_dir)

for img in val_images:
    shutil.copy(os.path.join(image_dir, img), val_img_dir)
    lbl = img.replace(".jpg", ".txt")
    if os.path.exists(os.path.join(label_dir, lbl)):
        shutil.copy(os.path.join(label_dir, lbl), val_lbl_dir)
