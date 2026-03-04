import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client


_supabase_client: Optional[Client] = None
_env_loaded = False


def _load_backend_env() -> None:
    """Load backend/.env once so local runs work from any working directory."""
    global _env_loaded
    if _env_loaded:
        return

    backend_root = Path(__file__).resolve().parents[2]
    load_dotenv(backend_root / ".env")
    _env_loaded = True


def get_supabase_client() -> Client:
    """Create and cache a Supabase client instance."""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    _load_backend_env()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

    _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client
