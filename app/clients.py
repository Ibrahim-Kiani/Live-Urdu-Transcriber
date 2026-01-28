"""External service clients and keys."""

import os
from typing import Optional

from groq import Groq

from .config import pick_groq_api_key

try:
    from supabase import create_client, Client
except ImportError:
    print("⚠️  Supabase not installed. Install with: pip install supabase")
    Client = None


groq_api_key = pick_groq_api_key()
if not groq_api_key:
    print("⚠️  Warning: GROQ_API_KEY not found in environment variables!")

groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_api_key:
    print("⚠️  Warning: OPENROUTER_API_KEY not found in environment variables!")

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

supabase_client: Optional["Client"] = None
if supabase_url and supabase_key:
    try:
        supabase_client = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"⚠️  Supabase connection failed: {e}")
else:
    print("⚠️  Supabase credentials not configured. Transcriptions won't be saved to database.")
