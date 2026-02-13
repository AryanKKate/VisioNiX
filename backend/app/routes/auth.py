from typing import Optional
from flask import Blueprint, jsonify, request
from supabase import AuthApiError

from app.services.supabase_client import get_supabase_client


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _extract_bearer_token(auth_header: str) -> Optional[str]:
    if not auth_header:
        return None

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


@auth_bp.route("/signup", methods=["POST"])
def signup():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_up({"email": email, "password": password})

        return jsonify(
            {
                "user": response.user.model_dump() if response.user else None,
                "session": response.session.model_dump() if response.session else None,
            }
        ), 201
    except (AuthApiError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"unexpected error: {exc}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

        return jsonify(
            {
                "user": response.user.model_dump() if response.user else None,
                "session": response.session.model_dump() if response.session else None,
            }
        )
    except (AuthApiError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 401
    except Exception as exc:
        return jsonify({"error": f"unexpected error: {exc}"}), 500


@auth_bp.route("/me", methods=["GET"])
def me():
    token = _extract_bearer_token(request.headers.get("Authorization", ""))
    if not token:
        return jsonify({"error": "Bearer token is required"}), 401

    try:
        supabase = get_supabase_client()
        user_response = supabase.auth.get_user(token)
        return jsonify({"user": user_response.user.model_dump() if user_response.user else None})
    except (AuthApiError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 401
    except Exception as exc:
        return jsonify({"error": f"unexpected error: {exc}"}), 500
