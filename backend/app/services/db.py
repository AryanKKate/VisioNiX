from datetime import datetime, timezone

from app.services.supabase_client import get_supabase_client


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_model_by_id(model_id):
    if not model_id:
        return None

    supabase = get_supabase_client()
    response = (
        supabase.table("models")
        .select("*")
        .eq("id", model_id)
        .limit(1)
        .execute()
    )

    rows = response.data or []
    return rows[0] if rows else None


def upsert_user_model(
    user_id: str,
    name: str,
    hf_space_url: str | None,
    task_type: str | None = None,
    status: str | None = None,
):
    """Create or update a model row for the authenticated user."""
    if not user_id or not name:
        return None

    supabase = get_supabase_client()
    minimal_payload = {
        "owner_id": user_id,
        "name": name,
        "is_default": False,
    }
    if hf_space_url is not None:
        minimal_payload["hf_space_url"] = hf_space_url

    # Some deployments have extra columns (task_type/status/updated_at), while
    # older schemas only have owner_id/name/is_default/hf_space_url.
    extended_payload = {
        **minimal_payload,
        "updated_at": _utc_now_iso(),
    }
    if task_type:
        extended_payload["task_type"] = task_type
    if status:
        extended_payload["status"] = status

    existing = (
        supabase.table("models")
        .select("*")
        .eq("owner_id", user_id)
        .eq("name", name)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    rows = existing.data or []
    if rows:
        model_id = rows[0].get("id")
        if model_id:
            try:
                updated = (
                    supabase.table("models")
                    .update(extended_payload)
                    .eq("id", model_id)
                    .execute()
                )
            except Exception:
                updated = (
                    supabase.table("models")
                    .update(minimal_payload)
                    .eq("id", model_id)
                    .execute()
                )

            updated_rows = updated.data or []
            return updated_rows[0] if updated_rows else rows[0]

    create_payload = {
        **minimal_payload,
        "created_at": _utc_now_iso(),
    }
    try:
        inserted = supabase.table("models").insert({**create_payload, **extended_payload}).execute()
    except Exception:
        inserted = supabase.table("models").insert(create_payload).execute()
    inserted_rows = inserted.data or []
    return inserted_rows[0] if inserted_rows else None
