
import jwt
from flask import request, jsonify
from functools import wraps

from app.config import Config


def require_supabase_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing token"}), 401

        token = auth_header.split(" ")[1]

        try:
            decoded = jwt.decode(token, Config.SUPABASE_JWT_SECRET, algorithms=[Config.SUPABASE_JWT_ALGORITHM])
        except Exception:
            return jsonify({"error": "Invalid token"}), 401

        request.user = decoded
        return f(*args, **kwargs)

    return wrapper