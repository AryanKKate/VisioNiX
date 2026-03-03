import base64
import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from supabase import AuthApiError

from app.services.ollama_service import generate_with_ollama
from app.services.supabase_client import get_supabase_client


chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


def _extract_bearer_token(auth_header: str):
    if not auth_header:
        return None

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def _get_user_from_request():
    token = _extract_bearer_token(request.headers.get("Authorization", ""))
    if not token:
        return None, (jsonify({"error": "Bearer token is required"}), 401)

    try:
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            return None, (jsonify({"error": "Invalid user session"}), 401)
        return user_response.user, None
    except (AuthApiError, ValueError) as exc:
        return None, (jsonify({"error": str(exc)}), 401)
    except Exception as exc:
        return None, (jsonify({"error": f"unexpected error: {exc}"}), 500)


def _suggest_chat_title(prompt: str):
    if not prompt:
        return "New Chat"

    words = prompt.strip().split()
    if not words:
        return "New Chat"
    return " ".join(words[:8])[:60]


@chat_bp.route("/rooms", methods=["GET"])
def list_rooms():
    user, error = _get_user_from_request()
    if error:
        return error

    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("chat_rooms")
            .select("id,title,created_at,updated_at")
            .eq("user_id", user.id)
            .order("updated_at", desc=True)
            .execute()
        )
        return jsonify({"rooms": response.data or []})
    except Exception as exc:
        return jsonify({"error": f"failed to list chat rooms: {exc}"}), 500


@chat_bp.route("/rooms", methods=["POST"])
def create_room():
    user, error = _get_user_from_request()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "New Chat").strip()[:80] or "New Chat"

    try:
        supabase = get_supabase_client()
        response = (
            supabase.table("chat_rooms")
            .insert({"user_id": user.id, "title": title})
            .execute()
        )
        room = response.data[0] if response.data else None
        return jsonify({"room": room}), 201
    except Exception as exc:
        return jsonify({"error": f"failed to create chat room: {exc}"}), 500


@chat_bp.route("/rooms/<room_id>", methods=["DELETE"])
def delete_room(room_id: str):
    user, error = _get_user_from_request()
    if error:
        return error

    try:
        supabase = get_supabase_client()
        room_check = (
            supabase.table("chat_rooms")
            .select("id")
            .eq("id", room_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
        if not room_check.data:
            return jsonify({"error": "chat room not found"}), 404

        supabase.table("chat_rooms").delete().eq("id", room_id).eq("user_id", user.id).execute()
        return jsonify({"status": "deleted"})
    except Exception as exc:
        return jsonify({"error": f"failed to delete chat room: {exc}"}), 500


@chat_bp.route("/rooms/<room_id>/messages", methods=["GET"])
def get_room_messages(room_id: str):
    user, error = _get_user_from_request()
    if error:
        return error

    try:
        supabase = get_supabase_client()
        room_check = (
            supabase.table("chat_rooms")
            .select("id")
            .eq("id", room_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
        if not room_check.data:
            return jsonify({"error": "chat room not found"}), 404

        response = (
            supabase.table("chat_messages")
            .select("id,room_id,role,content,image_name,image_mime_type,image_data,created_at")
            .eq("room_id", room_id)
            .order("created_at", desc=False)
            .execute()
        )
        return jsonify({"messages": response.data or []})
    except Exception as exc:
        return jsonify({"error": f"failed to fetch chat messages: {exc}"}), 500


@chat_bp.route("/rooms/<room_id>/messages", methods=["POST"])
def send_message(room_id: str):
    user, error = _get_user_from_request()
    if error:
        return error

    prompt = (request.form.get("prompt") or "").strip()
    model = (request.form.get("model") or "qwen3-vl:8b").strip() or "qwen3-vl:8b"

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    try:
        supabase = get_supabase_client()
        room_response = (
            supabase.table("chat_rooms")
            .select("id,title")
            .eq("id", room_id)
            .eq("user_id", user.id)
            .limit(1)
            .execute()
        )
        if not room_response.data:
            return jsonify({"error": "chat room not found"}), 404

        image_file = request.files.get("image")
        image_b64_for_reasoning = None
        image_name_for_reasoning = None
        image_mime_type_for_reasoning = None
        image_b64_for_message = None
        image_name_for_message = None
        image_mime_type_for_message = None

        if image_file and image_file.filename:
            image_name_for_reasoning = image_file.filename
            image_mime_type_for_reasoning = image_file.mimetype or "application/octet-stream"
            image_bytes = image_file.read()
            image_b64_for_reasoning = base64.b64encode(image_bytes).decode("ascii")
            image_name_for_message = image_name_for_reasoning
            image_mime_type_for_message = image_mime_type_for_reasoning
            image_b64_for_message = image_b64_for_reasoning
        else:
            # Reuse the most recent uploaded image in this room for follow-up queries.
            recent_messages = (
                supabase.table("chat_messages")
                .select("image_name,image_mime_type,image_data,created_at")
                .eq("room_id", room_id)
                .eq("role", "user")
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )
            for msg in recent_messages.data or []:
                if msg.get("image_data"):
                    image_b64_for_reasoning = msg.get("image_data")
                    image_name_for_reasoning = msg.get("image_name") or "previous_image"
                    image_mime_type_for_reasoning = msg.get("image_mime_type") or "application/octet-stream"
                    break

        user_message_payload = {
            "room_id": room_id,
            "role": "user",
            "content": prompt,
            "image_name": image_name_for_message,
            "image_mime_type": image_mime_type_for_message,
            "image_data": image_b64_for_message,
        }
        user_message_result = supabase.table("chat_messages").insert(user_message_payload).execute()
        user_message = user_message_result.data[0] if user_message_result.data else None

        image_path = None
        if image_b64_for_reasoning:
            os.makedirs("uploads/chat_images", exist_ok=True)
            image_path = os.path.join("uploads/chat_images", f"{uuid.uuid4()}_{image_name_for_reasoning}")
            with open(image_path, "wb") as out:
                out.write(base64.b64decode(image_b64_for_reasoning))
        else:
            return jsonify({"error": "Please upload an image to start this chat."}), 400

        try:
            assistant_text = generate_with_ollama(
                features={},
                image_path=image_path,
                user_prompt=prompt,
                ollama_model=model,
            )
        except Exception as exc:
            assistant_text = f"I could not complete that request right now: {exc}"

        assistant_message_payload = {
            "room_id": room_id,
            "role": "assistant",
            "content": assistant_text,
            "image_name": None,
            "image_mime_type": None,
            "image_data": None,
        }
        assistant_message_result = supabase.table("chat_messages").insert(assistant_message_payload).execute()
        assistant_message = (
            assistant_message_result.data[0] if assistant_message_result.data else None
        )

        room_title = room_response.data[0].get("title")
        if room_title == "New Chat":
            suggested_title = _suggest_chat_title(prompt)
            supabase.table("chat_rooms").update({"title": suggested_title}).eq("id", room_id).eq(
                "user_id", user.id
            ).execute()

        supabase.table("chat_rooms").update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", room_id).eq("user_id", user.id).execute()

        return jsonify(
            {
                "user_message": user_message,
                "assistant_message": assistant_message,
            }
        ), 201
    except Exception as exc:
        return jsonify({"error": f"failed to send message: {exc}"}), 500
