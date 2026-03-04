import requests
import json
import numpy as np
import os
import sys


# ==============================
# CONFIG
# ==============================

BASE_URL = "http://127.0.0.1:5000"   # Change if deployed
ENDPOINT = f"{BASE_URL}/extract"

IMAGE_PATH = "apple.webp"

# Optional (set both to None to test local model fallback)
MODEL_ID = "c5bd9bc6-f311-4f4a-9cb2-2b426170c820"       # Example: "abc123"
USER_ID = ""         # Example: "user_1"


# ==============================
# TEST FUNCTION
# ==============================

def test_extract_route():

    if not os.path.exists(IMAGE_PATH):
        print("❌ Image file not found:", IMAGE_PATH)
        sys.exit(1)

    print("🚀 Testing:", ENDPOINT)

    files = {
        "image": open(IMAGE_PATH, "rb")
    }

    data = {}

    if MODEL_ID and USER_ID:
        data["model_id"] = MODEL_ID
        data["user_id"] = USER_ID
        print("🧠 Using remote HF model")
    else:
        print("🖥 Using local default model")

    try:
        response = requests.post(
            ENDPOINT,
            files=files,
            data=data,
            timeout=180
        )

        print("\n📡 Status Code:", response.status_code)

        try:
            result = response.json()
        except Exception:
            print("❌ Response not JSON:")
            print(response.text)
            return

        print("\n✅ Response:")
        print(json.dumps(result, indent=2))

        # ==============================
        # Basic Validations
        # ==============================

        required_keys = [
            "caption",
            "objects",
            "scene_labels",
            "clip_embedding_file",
            "clip_embedding_path",
            "embed"
        ]

        missing = [k for k in required_keys if k not in result]

        if missing:
            print("\n⚠️ Missing keys:", missing)
        else:
            print("\n✔ All required keys present")

        if "embed" in result:
            embedding = np.array(result["embed"])
            print("📐 Embedding shape:", embedding.shape)

        print("\n🎉 Extraction route working")

    except Exception as e:
        print("\n❌ Error during request:")
        print(str(e))


if __name__ == "__main__":
    test_extract_route()