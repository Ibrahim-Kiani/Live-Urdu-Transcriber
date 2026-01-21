"""
Real-time Urdu to English Audio Translation API
Uses Groq's Whisper model for audio translation
"""

import os
import tempfile
from pathlib import Path
import random
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

model_name = "whisper-large-v3"
apis = ["GROQ_API_KEY", "GROQ2_API_KEY"]
# Initialize FastAPI app
app = FastAPI(
    title="Urdu Audio Translator",
    description="Real-time Urdu to English audio translation using Groq Whisper",
    version="1.0.0"
)

# Configure CORS for mobile and cross-origin access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Initialize Groq client
groq_api_key = os.getenv(random.choice(apis))
if not groq_api_key:
    print("⚠️  Warning: GROQ_API_KEY not found in environment variables!")
    print("   Please create a .env file with your GROQ_API_KEY")

client = Groq(api_key=groq_api_key) if groq_api_key else None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main application page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/translate")
async def translate_audio(audio: UploadFile = File(...)):
    """
    Translate audio from Urdu to English
    
    Accepts audio file (webm, wav, mp3, etc.) and returns English translation
    using Groq's Whisper large-v3 model
    """
    if not client:
        raise HTTPException(
            status_code=500,
            detail="Groq API key not configured. Please set GROQ_API_KEY in .env file"
        )
    
    # Validate file type
    allowed_types = [
        "audio/webm", "audio/wav", "audio/mp3", "audio/mpeg",
        "audio/ogg", "audio/flac", "audio/m4a", "video/webm"
    ]
    
    content_type = audio.content_type or "audio/webm"
    if not any(t in content_type for t in ["audio", "video/webm"]):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {content_type}. Expected audio file."
        )
    
    try:
        # Read the audio content
        audio_content = await audio.read()
        
        # Much stricter validation - require at least 5KB of audio
        # (silence or very quiet audio gets rejected here)
        if len(audio_content) < 5000:
            return {"text": "", "status": "too_short"}
        
        # Create a temporary file to store the audio
        # Groq API requires a file-like object with a name
        suffix = ".webm" if "webm" in content_type else ".wav"
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(audio_content)
            temp_file_path = temp_file.name
        
        try:
            # Open the temp file and send to Groq for translation
            with open(temp_file_path, "rb") as audio_file:
                # Use translations endpoint - automatically translates to English
                # NOTE: Only whisper-large-v3 supports translations. whisper-large-v3-turbo does not.
                translation = client.audio.translations.create(
                    model=model_name,
                    file=audio_file,
                    response_format="text"
                )
            # Clean up the translated text
            translated_text = str(translation).strip()
            
            return {
                "text": translated_text,
                "status": "success"
            }
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
                
    except Exception as e:
        error_message = str(e)
        print(f"Translation error: {error_message}")
        
        # Handle specific Groq API errors
        if "Invalid API Key" in error_message:
            raise HTTPException(status_code=401, detail="Invalid Groq API key")
        elif "rate limit" in error_message.lower():
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait.")
        else:
            raise HTTPException(status_code=500, detail=f"Translation failed: {error_message}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "groq_configured": client is not None
    }


if __name__ == "__main__":
    import uvicorn
    print("\n🎙️  Urdu Audio Translator Starting...")
    print("📍 Open http://localhost:8000 in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
