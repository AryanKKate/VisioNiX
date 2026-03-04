from typing import Optional
from app.services.supabase_client import get_supabase_client


def get_model_by_id(model_id):
    supabase=get_supabase_client()
    response = (
        supabase
        .table("models")
        .select("*")
        .eq("id", model_id)
        .single()
        .execute()
    )

    if response.data:
        return response.data

    return None