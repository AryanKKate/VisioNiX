import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # SECRET_KEY = os.getenv("SECRET_KEY")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")
    EMBEDDING_FOLDER = os.getenv("EMBEDDING_FOLDER")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
