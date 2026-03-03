from ultralytics import YOLO
import cv2
import os

# Load trained model
model = YOLO("runs/detect/train11/weights/best.pt")

def detect_pneumonia(image_path, save_path="outputs"):
    results = model(image_path, imgsz=768, conf=0.25)

    os.makedirs(save_path, exist_ok=True)

    for r in results:
        output_path = os.path.join(save_path, os.path.basename(image_path))
        r.save(filename=output_path)

    return results

if __name__ == "__main__":
    test_image = "test_pneumonia.jpg" 
    results = detect_pneumonia(test_image)
    print("Detection completed.")