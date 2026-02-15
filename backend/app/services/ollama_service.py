import base64
import logging
import os
import json
from typing import Any

import requests

logger = logging.getLogger(__name__)


def _wants_brief_response(query: str) -> bool:
    q = (query or "").lower()
    brief_keywords = (
        "brief",
        "short",
        "concise",
        "one line",
        "single line",
        "in short",
        "tldr",
        "summarize",
        "summary",
    )
    return any(k in q for k in brief_keywords)


def _is_sufficient_response(text: str, query: str, min_chars: int) -> bool:
    content = (text or "").strip()
    if not content:
        return False
    if _wants_brief_response(query):
        return True
    return len(content) >= min_chars


def _build_prompt(features: dict, user_prompt: str | None = None) -> str:
    query = (user_prompt or "").strip() or "Describe this image in detail."
    brief_mode = _wants_brief_response(query)
    style_policy = (
        "- Write in complete paragraphs.\n"
        "- Keep the answer concise (2-5 sentences) because the user asked for brief output.\n"
        "- Do not use bullet points unless the user explicitly asks for bullets.\n"
    ) if brief_mode else (
        "- Write in complete paragraphs.\n"
        "- By default provide 3-5 well-structured paragraphs with reasoning.\n"
        "- Target roughly 220-350 words unless the user asks for a shorter answer.\n"
        "- Do not use bullet points unless the user explicitly asks for bullets.\n"
        "- Do not stop mid-sentence.\n"
    )
    return (
        "You are a visual reasoning assistant. Use both the uploaded image and the provided structured signals "
        "to answer the user's query accurately.\n\n"
        "Response style policy:\n"
        f"{style_policy}"
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
    num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "1024"))
    min_detailed_chars = int(os.getenv("OLLAMA_MIN_DETAILED_CHARS", "260"))

    prompt = _build_prompt(features, user_prompt=user_prompt)
    query_text = (user_prompt or "").strip() or "Describe this image in detail."
    image_b64 = _encode_image_base64(image_path)
    candidates: list[str] = []

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
            candidates.append(content)
        if _is_sufficient_response(content, query_text, min_detailed_chars):
            return content
        logger.warning(
            json.dumps(
                {
                    "event": "ollama_empty_response",
                    "endpoint": "chat_primary",
                    "model": model_name,
                    "reason": "empty_or_too_short",
                    "length": len((content or "").strip()),
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
        "Answer the user's query directly using the image. "
        "Your previous answer was too short. "
        "Now provide 3-5 detailed paragraphs (around 220-350 words) with clear reasoning and concrete visual evidence. "
        "Do not use bullets unless asked. Do not stop mid-sentence. "
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
            candidates.append(retry_content)
        if _is_sufficient_response(retry_content, query_text, min_detailed_chars):
            return retry_content
        logger.warning(
            json.dumps(
                {
                    "event": "ollama_empty_response",
                    "endpoint": "chat_retry",
                    "model": model_name,
                    "reason": "empty_or_too_short",
                    "length": len((retry_content or "").strip()),
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
            candidates.append(generate_content)
        if _is_sufficient_response(generate_content, query_text, min_detailed_chars):
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

    if candidates:
        candidates.sort(key=lambda c: len((c or "").strip()), reverse=True)
        return candidates[0].strip()

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
