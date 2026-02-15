import base64
import logging
import os
import json
from typing import Any

import requests

logger = logging.getLogger(__name__)


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


def _post_json(
    url: str,
    payload: dict[str, Any],
    timeout: int,
    max_retries: int,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                json.dumps(
                    {
                    "event": "ollama_request_failed",
                    "attempt": attempt + 1,
                    "max_attempts": max_retries + 1,
                    "url": url,
                    "error": str(exc),
                    "context": context or {},
                    }
                )
            )
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Ollama request failed without exception")


def generate_with_ollama(
    features: dict,
    image_path: str,
    user_prompt: str | None = None,
    ollama_model: str | None = None,
) -> str:
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = ollama_model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    max_retries = int(os.getenv("OLLAMA_MAX_RETRIES", "1"))

    prompt = _build_prompt(features, user_prompt=user_prompt)
    image_b64 = _encode_image_base64(image_path)

    chat_url = f"{ollama_base_url}/api/chat"
    generate_url = f"{ollama_base_url}/api/generate"

    try:
        chat_data = _post_json(
            chat_url,
            {
                "model": model_name,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_b64],
                    }
                ],
            },
            timeout=timeout,
            max_retries=max_retries,
            context={"endpoint": "chat", "model": model_name},
        )
        message = chat_data.get("message", {})
        content = message.get("content", "")
        if content:
            return content
    except requests.RequestException:
        logger.info(
            json.dumps(
                {
                "event": "ollama_chat_fallback_to_generate",
                "model": model_name,
                }
            )
        )

    generate_data = _post_json(
        generate_url,
        {"model": model_name, "prompt": prompt, "stream": False},
        timeout=timeout,
        max_retries=max_retries,
        context={"endpoint": "generate", "model": model_name},
    )
    return generate_data.get("response", "")


def check_ollama_health(ollama_model: str | None = None) -> dict[str, Any]:
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = ollama_model or os.getenv("OLLAMA_MODEL", "qwen3-vl:8b")
    timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "10"))
    max_retries = int(os.getenv("OLLAMA_MAX_RETRIES", "0"))

    chat_url = f"{ollama_base_url}/api/chat"
    data = _post_json(
        chat_url,
        {
            "model": model_name,
            "stream": False,
            "messages": [{"role": "user", "content": "Reply with: OK"}],
        },
        timeout=timeout,
        max_retries=max_retries,
        context={"endpoint": "health", "model": model_name},
    )
    content = data.get("message", {}).get("content", "")
    return {
        "status": "ok",
        "base_url": ollama_base_url,
        "model": model_name,
        "response_preview": content[:60],
    }
