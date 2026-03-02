# from app.models import predict_severity

# result = predict_severity("upload_img/test_xray.jpg")
# print(result)

import os

dicom_path = "data/rsna/dicom/stage_2_train_images"
print("Total DICOM images:", len(os.listdir(dicom_path)))