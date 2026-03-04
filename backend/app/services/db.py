from app.services.supabase_client import get_supabase_client


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
