"""
Real-time Urdu to English Audio Translation API
Uses Groq's Whisper model for audio translation and LLaMA for title generation
Stores transcriptions in Supabase PostgreSQL database
"""

import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from dotenv import load_dotenv
from groq import Groq

try:
    from supabase import create_client, Client
except ImportError:
    print("⚠️  Supabase not installed. Install with: pip install supabase")
    Client = None

# Load environment variables
load_dotenv()

# Constants
TRANSLATION_MODEL = "whisper-large-v3"
TITLE_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Pydantic models for request/response
class CreateLectureRequest(BaseModel):
    lecture_name: str

class StartRecordingResponse(BaseModel):
    lecture_id: int
    lecture_name: str
    status: str

class EndRecordingRequest(BaseModel):
    lecture_id: int

class TranslationResponse(BaseModel):
    text: str
    status: str
    lecture_id: Optional[int] = None
    chunk_number: Optional[int] = None

# Initialize FastAPI app
app = FastAPI(
    title="Urdu Audio Translator",
    description="Real-time Urdu to English audio translation with LLaMA title generation",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Initialize Groq client
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("⚠️  Warning: GROQ_API_KEY not found in environment variables!")

groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

supabase_client: Optional[Client] = None
if supabase_url and supabase_key:
    try:
        supabase_client = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"⚠️  Supabase connection failed: {e}")
else:
    print("⚠️  Supabase credentials not configured. Transcriptions won't be saved to database.")

# Global state for tracking lectures and chunks
lectures_state = {}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main application page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/lecture/create", response_model=StartRecordingResponse)
async def create_lecture(request: CreateLectureRequest):
    """Create a new lecture session"""
    try:
        if not supabase_client:
            raise HTTPException(
                status_code=500,
                detail="Database not configured. Please set SUPABASE_URL and SUPABASE_KEY"
            )
        
        # Insert into lectures table
        response = supabase_client.table("lectures").insert({
            "lecture_name": request.lecture_name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        
        if response.data:
            lecture_id = response.data[0]["id"]
            lectures_state[lecture_id] = {
                "lecture_name": request.lecture_name,
                "chunk_count": 0,
                "full_transcript": ""
            }
            
            return StartRecordingResponse(
                lecture_id=lecture_id,
                lecture_name=request.lecture_name,
                status="success"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create lecture")
            
    except Exception as e:
        error_msg = str(e)
        print(f"Lecture creation error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to create lecture: {error_msg}")


@app.post("/translate")
async def translate_audio(
    audio: UploadFile = File(...),
    lecture_id: Optional[int] = None,
    chunk_number: Optional[int] = None
):
    """
    Translate audio from Urdu to English
    
    Accepts audio file and returns English translation.
    Optionally saves to database if lecture_id is provided.
    """
    if not groq_client:
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
        # Read and validate audio
        audio_content = await audio.read()
        
        if len(audio_content) < 5000:
            return {"text": "", "status": "too_short"}
        
        # Create temporary file
        suffix = ".webm" if "webm" in content_type else ".wav"
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(audio_content)
            temp_file_path = temp_file.name
        
        try:
            # Call Groq for translation
            with open(temp_file_path, "rb") as audio_file:
                translation = groq_client.audio.translations.create(
                    model=TRANSLATION_MODEL,
                    file=audio_file,
                    response_format="text"
                )
            
            translated_text = str(translation).strip()
            
            # Save to database if lecture_id provided
            if lecture_id and supabase_client and translated_text:
                try:
                    supabase_client.table("transcriptions").insert({
                        "lecture_id": lecture_id,
                        "chunk_number": chunk_number or 0,
                        "english_text": translated_text,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "timestamps": {
                            "recorded_at": datetime.now(timezone.utc).isoformat()
                        }
                    }).execute()
                    
                    # Update lecture state
                    if lecture_id in lectures_state:
                        lectures_state[lecture_id]["chunk_count"] += 1
                        lectures_state[lecture_id]["full_transcript"] += " " + translated_text
                        
                except Exception as db_error:
                    print(f"Database save error: {db_error}")
                    # Continue even if database save fails
            
            return TranslationResponse(
                text=translated_text,
                status="success",
                lecture_id=lecture_id,
                chunk_number=chunk_number
            )
            
        finally:
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
                
    except Exception as e:
        error_message = str(e)
        print(f"Translation error: {error_message}")
        
        if "Invalid API Key" in error_message:
            raise HTTPException(status_code=401, detail="Invalid Groq API key")
        elif "rate limit" in error_message.lower():
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait.")
        else:
            raise HTTPException(status_code=500, detail=f"Translation failed: {error_message}")


@app.post("/lecture/end")
async def end_recording(request: EndRecordingRequest):
    """
    End recording and generate title using LLaMA
    """
    try:
        lecture_id = request.lecture_id
        
        if lecture_id not in lectures_state:
            raise HTTPException(status_code=404, detail="Lecture not found")
        
        if not groq_client:
            raise HTTPException(status_code=500, detail="Groq API not configured")
        
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        # Get full transcript from database
        transcript_response = supabase_client.table("transcriptions").select(
            "english_text"
        ).eq("lecture_id", lecture_id).order("chunk_number").execute()
        
        if not transcript_response.data:
            # Use from memory if no DB records
            full_transcript = lectures_state[lecture_id]["full_transcript"]
        else:
            full_transcript = " ".join([
                item["english_text"] for item in transcript_response.data
            ])
        
        if not full_transcript.strip():
            raise HTTPException(status_code=400, detail="No transcript available")
        
        # Generate title using LLaMA
        print(f"Generating title for lecture {lecture_id}...")
        
        title_prompt = f"""Based on the following lecture transcript, generate a concise and descriptive title (max 10 words) for this lecture.

Transcript:
{full_transcript[:2000]}...

Title:"""
        
        title_response = groq_client.chat.completions.create(
            model=TITLE_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": title_prompt
                }
            ],
            max_tokens=50,
            temperature=0.5
        )
        
        generated_title = title_response.choices[0].message.content.strip()
        
        # Update lecture with title and end time
        update_response = supabase_client.table("lectures").update({
            "generated_title": generated_title,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "full_transcript": full_transcript,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", lecture_id).execute()
        
        # Clean up state
        if lecture_id in lectures_state:
            del lectures_state[lecture_id]
        
        return {
            "lecture_id": lecture_id,
            "generated_title": generated_title,
            "transcript_chunks": len(transcript_response.data) if transcript_response.data else 0,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"End recording error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to end recording: {error_msg}")


@app.get("/lecture/{lecture_id}")
async def get_lecture(lecture_id: int):
    """Get lecture details and transcriptions"""
    try:
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        # Get lecture
        lecture_response = supabase_client.table("lectures").select(
            "*"
        ).eq("id", lecture_id).single().execute()
        
        if not lecture_response.data:
            raise HTTPException(status_code=404, detail="Lecture not found")
        
        # Get transcriptions
        transcriptions_response = supabase_client.table("transcriptions").select(
            "*"
        ).eq("lecture_id", lecture_id).order("chunk_number").execute()
        
        return {
            "lecture": lecture_response.data,
            "transcriptions": transcriptions_response.data,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Get lecture error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lecture: {error_msg}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "groq_configured": groq_client is not None,
        "database_configured": supabase_client is not None
    }


if __name__ == "__main__":
    import uvicorn
    print("\n🎙️  Urdu Audio Translator Starting...")
    print("📍 Open http://localhost:8000 in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
