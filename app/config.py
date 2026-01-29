"""Configuration and constants."""

import os
import random
from dotenv import load_dotenv

load_dotenv()

TRANSLATION_MODEL = "whisper-large-v3"
TRANSCRIPTION_MODEL = "whisper-large-v3"
TITLE_MODEL = "llama-3.3-70b-versatile"
ENHANCEMENT_MODEL = "tngtech/tng-r1t-chimera:free"
REFINED_TRANSLATION_MODEL = "openai/gpt-oss-120b"

GROQ_API_KEYS = ["GROQ_API_KEY", "GROQ2_API_KEY"]


def pick_groq_api_key() -> str | None:
    """Select a Groq API key at random from supported env vars."""
    return os.getenv(random.choice(GROQ_API_KEYS))
