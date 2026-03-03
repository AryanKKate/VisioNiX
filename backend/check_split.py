import os

for split in ["train", "val"]:
    img_dir = f"data/rsna/images/{split}"
    label_dir = f"data/rsna/labels/{split}"

    total_images = len(os.listdir(img_dir))
    total_labels = len(os.listdir(label_dir))

    print("\n" + split.upper())
    print("Images:", total_images)
    print("Label files:", total_labels)