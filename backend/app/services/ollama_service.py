import base64
import os
from typing import Any

import requests


def _build_prompt(features: dict, user_prompt: str | None = None) -> str:
    base_prompt = (
        "You are an assistant that explains image-analysis results in simple language. "
        "Use both the image and the provided structured features.\n\n"
        f"Caption: {features.get('caption', '')}\n"
        f"Objects: {features.get('objects', [])}\n"
        f"OCR Text: {features.get('ocr_text', '')}\n"
        f"Scene Labels: {features.get('scene_labels', [])}\n"
        f"Mean Color: {features.get('color_features', [])}\n"
        f"Texture: {features.get('texture_features', [])}\n\n"
        "Output format:\n"
        "1) Summary (2-4 lines)\n"
        "2) Key tags (comma-separated)\n"
        "3) Suggested search query (one line)"
    )
    if user_prompt:
        return f"{base_prompt}\n\nExtra user instruction: {user_prompt}"
    return base_prompt


def _encode_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _post_json(url: str, payload: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def generate_with_ollama(
    features: dict,
    image_path: str,
    user_prompt: str | None = None,
) -> str:
    """Generate a natural-language response using Ollama vision models when available."""
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen3vl:8b")

    prompt = _build_prompt(features, user_prompt=user_prompt)
    image_b64 = _encode_image_base64(image_path)

    chat_url = f"{ollama_base_url}/api/chat"
    generate_url = f"{ollama_base_url}/api/generate"

    try:
        chat_data = _post_json(
            chat_url,
            {
                "model": ollama_model,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_b64],
                    }
                ],
            },
        )
        message = chat_data.get("message", {})
        content = message.get("content", "")
        if content:
            return content
    except requests.RequestException:
        # Fallback for non-vision models/endpoints.
        pass

    generate_data = _post_json(
        generate_url,
        {"model": ollama_model, "prompt": prompt, "stream": False},
    )
    return generate_data.get("response", "")
