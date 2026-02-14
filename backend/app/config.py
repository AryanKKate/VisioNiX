import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # SECRET_KEY = os.getenv("SECRET_KEY")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")
    EMBEDDING_FOLDER = os.getenv("EMBEDDING_FOLDER")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-vl:8b")
    OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "1"))
    DESCRIBE_RUNS_LOG_PATH = os.getenv(
        "DESCRIBE_RUNS_LOG_PATH", "logs/describe_runs.jsonl"
    )
