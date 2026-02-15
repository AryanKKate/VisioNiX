import base64
import logging
import os
import json
from typing import Any

import requests

logger = logging.getLogger(__name__)


def _build_prompt(features: dict, user_prompt: str | None = None) -> str:
    query = (user_prompt or "").strip() or "Describe this image in detail."
    return (
        "You are a visual reasoning assistant. Use both the uploaded image and the provided structured signals "
        "to answer the user's query accurately.\n\n"
        "Response style policy:\n"
        "- Write in complete paragraphs.\n"
        "- By default provide 2-3 well-structured paragraphs with reasoning.\n"
        "- Do not use bullet points unless the user explicitly asks for bullets.\n"
        "- If the user asks for brief output, keep it brief.\n\n"
        "Output policy:\n"
        "- Return only the answer to the user query.\n"
        "- Do not force fixed templates (no mandatory Summary/Key tags/Search query sections).\n"
        "- If uncertain, say so briefly and avoid hallucinating.\n\n"
        f"User query: {query}\n\n"
        "Structured signals:\n"
        f"Caption: {features.get('caption', '')}\n"
        f"Objects: {features.get('objects', [])}\n"
        f"OCR Text: {features.get('ocr_text', '')}\n"
        f"Scene Labels: {features.get('scene_labels', [])}\n"
        f"Mean Color: {features.get('color_features', [])}\n"
        f"Texture: {features.get('texture_features', [])}\n"
    )


def _encode_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _extract_text(payload: dict[str, Any]) -> str:
    message = payload.get("message", {})
    if isinstance(message, dict):
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()

    response = payload.get("response", "")
    if isinstance(response, str) and response.strip():
        return response.strip()

    return ""


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
    num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))

    prompt = _build_prompt(features, user_prompt=user_prompt)
    query_text = (user_prompt or "").strip() or "Describe this image in detail."
    image_b64 = _encode_image_base64(image_path)

    chat_url = f"{ollama_base_url}/api/chat"
    generate_url = f"{ollama_base_url}/api/generate"

    try:
        chat_data = _post_json(
            chat_url,
            {
                "model": model_name,
                "stream": False,
                "options": {"num_predict": num_predict},
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
            context={"endpoint": "chat_primary", "model": model_name},
        )
        content = _extract_text(chat_data)
        if content:
            return content
        logger.warning(
            json.dumps(
                {
                    "event": "ollama_empty_response",
                    "endpoint": "chat_primary",
                    "model": model_name,
                }
            )
        )
    except requests.RequestException:
        logger.info(
            json.dumps(
                {
                    "event": "ollama_chat_fallback_to_retry",
                    "model": model_name,
                }
            )
        )

    retry_prompt = (
        "Answer the user's query directly using the image in complete paragraphs. "
        "Provide 2-3 concise paragraphs by default. "
        "If uncertain, say so briefly.\n\n"
        f"User query: {query_text}"
    )
    try:
        retry_data = _post_json(
            chat_url,
            {
                "model": model_name,
                "stream": False,
                "options": {"num_predict": num_predict},
                "messages": [
                    {
                        "role": "user",
                        "content": retry_prompt,
                        "images": [image_b64],
                    }
                ],
            },
            timeout=timeout,
            max_retries=max_retries,
            context={"endpoint": "chat_retry", "model": model_name},
        )
        retry_content = _extract_text(retry_data)
        if retry_content:
            return retry_content
        logger.warning(
            json.dumps(
                {
                    "event": "ollama_empty_response",
                    "endpoint": "chat_retry",
                    "model": model_name,
                }
            )
        )
    except requests.RequestException:
        logger.info(
            json.dumps(
                {
                    "event": "ollama_chat_retry_fallback_to_generate",
                    "model": model_name,
                }
            )
        )

    try:
        generate_data = _post_json(
            generate_url,
            {
                "model": model_name,
                "prompt": retry_prompt,
                "images": [image_b64],
                "stream": False,
                "options": {"num_predict": num_predict},
            },
            timeout=timeout,
            max_retries=max_retries,
            context={"endpoint": "generate_fallback", "model": model_name},
        )
        generate_content = _extract_text(generate_data)
        if generate_content:
            return generate_content
    except requests.RequestException:
        logger.warning(
            json.dumps(
                {
                    "event": "ollama_generate_fallback_failed",
                    "model": model_name,
                }
            )
        )

    caption = str(features.get("caption", "")).strip()
    if caption:
        return f"I could not get a full model response. Basic visual summary: {caption}"
    return "I could not get a response from Ollama. Please try again."


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
