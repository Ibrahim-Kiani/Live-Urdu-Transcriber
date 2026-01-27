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

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from dotenv import load_dotenv
from groq import Groq
import httpx
import random

try:
    from supabase import create_client, Client
except ImportError:
    print("⚠️  Supabase not installed. Install with: pip install supabase")
    Client = None

# Load environment variables
load_dotenv()

# Constants
TRANSLATION_MODEL = "whisper-large-v3"
TRANSCRIPTION_MODEL = "whisper-large-v3"
TITLE_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
ENHANCEMENT_MODEL = "tngtech/tng-r1t-chimera:free"
REFINED_TRANSLATION_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"

# Pydantic models for request/response
class CreateLectureRequest(BaseModel):
    lecture_name: str

class StartRecordingResponse(BaseModel):
    lecture_id: int
    lecture_name: str
    status: str

class EndRecordingRequest(BaseModel):
    lecture_id: int


class EnhanceLectureRequest(BaseModel):
    lecture_id: int

class TranslationResponse(BaseModel):
    text: str
    refined_text: Optional[str] = None
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
groq_api_key = os.getenv(random.choice(["GROQ_API_KEY","GROQ2_API_KEY"]))
if not groq_api_key:
    print("⚠️  Warning: GROQ_API_KEY not found in environment variables!")

groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# Initialize OpenRouter client
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_api_key:
    print("⚠️  Warning: OPENROUTER_API_KEY not found in environment variables!")

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


async def enhance_transcript(title: str, raw_transcript: str) -> Optional[str]:
    """Use OpenRouter to refine the transcript."""
    if not openrouter_api_key:
        return None


def refine_urdu_transcript(raw_urdu_text: str) -> Optional[str]:
    """Use Groq LLM to translate Urdu transcript into refined English."""
    if not groq_client:
        return None

    system_prompt = (
        "You are an expert Urdu-to-English interpreter specializing in technical discourse. "
        "You will receive a raw transcription in Urdu. Your goal is to provide a fluent, grammatically correct English translation.\n\n"
        "The Context: The speaker is discussing [e.g., Data Science and Data Mining].\n\n"
        "Your Tasks:\n\n"
        "Literal vs. Intentional: If the raw text contains \"nonsensical\" phrases or poor grammar, "
        "infer the speaker's intent based on the surrounding technical context.\n\n"
        "Smoothing: Fix run-on sentences and ensure the flow sounds like a professional lecture or discussion.\n\n"
        "Output: Provide only the refined English translation."
    )

    user_prompt = f"Input (Urdu Transcription): {raw_urdu_text}"

    try:
        response = groq_client.chat.completions.create(
            model=REFINED_TRANSLATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1200
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception as e:
        print(f"Refined translation error: {e}")
        return None

    prompt = (
        "Role: You are a Technical Transcript Editor specializing in Machine Learning and Computer Science lectures.\n"
        "Task: Your goal is to take a raw, machine-translated transcript from an Urdu-to-English system and "
        "\"reconstruct\" it into a professional, readable English transcript.\n\n"
        f"Title: {title}\n"
        f"Raw Transcript: {raw_transcript}\n\n"
        "Guidelines for Refinement:\n"
        "- Preserve Semantic Meaning: Do not add new information or remove existing concepts. The goal is to make the existing content coherent.\n"
        "- Fix \"Phonetic\" and Translation Errors: Machine translations often misinterpret technical terms (e.g., \"Wright Next\" usually means \"Right, next,\" and \"linear length\" might mean \"linear regression\"). Use the Title to make educated guesses for these technical corrections.\n"
        "- Repair Sentence Structure: Convert disjointed, repetitive phrases into smooth, grammatically correct English. (e.g., \"on the basis of the rules, the machine has taken out the rules\" $\rightarrow$ \"Based on these rules, the machine has extracted patterns...\").\n"
        "- Maintain Lecture Tone: Keep the instructional and conversational feel, but remove unnecessary fillers or extreme redundancies that don't add value.\n\n"
        "Formatting:\n"
        "- Use Paragraphs to separate distinct ideas.\n"
        "- Use Bold for key technical terms.\n"
        "- Use LaTeX for any mathematical formulas (e.g., $y = wx + b$).\n\n"
        "Output Format: Return only the refined transcript. If a specific section is completely nonsensical even with context, place the best-guess interpretation in [brackets]."
    )

    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Live Urdu Transcriber"
    }

    payload = {
        "model": ENHANCEMENT_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 2000
    }

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip() if content else None
    except Exception as e:
        print(f"Enhancement error: {e}")
        return None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the lecture history page as the landing page"""
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    """Serve the lecture history page"""
    return templates.TemplateResponse("history.html", {"request": request})


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
    lecture_id: Optional[str] = Form(None),
    chunk_number: Optional[str] = Form(None)
):
    """
    Translate audio from Urdu to English
    
    Accepts audio file and returns English translation.
    Optionally saves to database if lecture_id is provided.
    """
    # Convert form data strings to integers
    lecture_id_int = int(lecture_id) if lecture_id else None
    chunk_number_int = int(chunk_number) if chunk_number else None
    
    print(f"📝 Translation request - lecture_id: {lecture_id_int}, chunk_number: {chunk_number_int}")
    
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
            # Call Groq for translation (direct Urdu -> English)
            with open(temp_file_path, "rb") as audio_file:
                translation = groq_client.audio.translations.create(
                    model=TRANSLATION_MODEL,
                    file=audio_file,
                    response_format="text"
                )
            
            translated_text = str(translation).strip()

            # Call Groq for transcription (Urdu) -> LLM refinement to English
            with open(temp_file_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    model=TRANSCRIPTION_MODEL,
                    file=audio_file,
                    response_format="text"
                )

            urdu_transcript = str(transcription).strip()
            refined_text = refine_urdu_transcript(urdu_transcript) if urdu_transcript else None
            
            print(f"✅ Translated: {translated_text[:100]}...")
            
            # Save to database if lecture_id provided
            if lecture_id_int and supabase_client and translated_text:
                try:
                    print(f"💾 Saving to database - lecture_id: {lecture_id_int}, chunk: {chunk_number_int}")
                    
                    result = supabase_client.table("transcriptions").insert({
                        "lecture_id": lecture_id_int,
                        "chunk_number": chunk_number_int or 0,
                        "english_text": translated_text,
                        "is_gpt_refined": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "timestamps": {
                            "recorded_at": datetime.now(timezone.utc).isoformat()
                        }
                    }).execute()
                    
                    print(f"✅ Saved to database successfully: {result.data}")
                    
                    # Update lecture state (original translation only)
                    if lecture_id_int in lectures_state:
                        lectures_state[lecture_id_int]["chunk_count"] += 1
                        lectures_state[lecture_id_int]["full_transcript"] += " " + translated_text
                        print(f"📊 Updated state - chunks: {lectures_state[lecture_id_int]['chunk_count']}")
                        
                except Exception as db_error:
                    print(f"❌ Database save error: {db_error}")
                    import traceback
                    traceback.print_exc()
                    # Continue even if database save fails
            else:
                if not lecture_id_int:
                    print("⚠️  No lecture_id provided, skipping database save")
            
            # Save refined transcript if available
            if lecture_id_int and supabase_client and refined_text:
                try:
                    supabase_client.table("transcriptions").insert({
                        "lecture_id": lecture_id_int,
                        "chunk_number": chunk_number_int or 0,
                        "english_text": refined_text,
                        "is_gpt_refined": True,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "timestamps": {
                            "recorded_at": datetime.now(timezone.utc).isoformat()
                        }
                    }).execute()
                except Exception as db_error:
                    print(f"❌ Refined save error: {db_error}")
                    import traceback
                    traceback.print_exc()

            return TranslationResponse(
                text=translated_text,
                refined_text=refined_text,
                status="success",
                lecture_id=lecture_id_int,
                chunk_number=chunk_number_int
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
        
        print(f"🔚 Ending lecture {lecture_id}")
        print(f"📊 Lectures state: {lectures_state}")
        
        if lecture_id not in lectures_state:
            print(f"❌ Lecture {lecture_id} not found in state. Available: {list(lectures_state.keys())}")
            raise HTTPException(status_code=404, detail="Lecture not found in session state")
        
        if not groq_client:
            raise HTTPException(status_code=500, detail="Groq API not configured")
        
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not configured")
        
        # Get full transcript from database
        print(f"🔍 Fetching transcriptions from database for lecture {lecture_id}")
        transcript_response = supabase_client.table("transcriptions").select(
            "english_text"
        ).eq("lecture_id", lecture_id).eq("is_gpt_refined", False).order("chunk_number").execute()
        
        print(f"📝 Found {len(transcript_response.data) if transcript_response.data else 0} transcriptions in database")
        
        if not transcript_response.data:
            # Use from memory if no DB records
            print("⚠️  No database records, using in-memory transcript")
            full_transcript = lectures_state[lecture_id]["full_transcript"]
        else:
            full_transcript = " ".join([
                item["english_text"] for item in transcript_response.data
            ])
        
        print(f"📄 Full transcript length: {len(full_transcript)} characters")
        print(f"📄 Transcript preview: {full_transcript[:200]}...")
        
        if not full_transcript.strip():
            raise HTTPException(status_code=400, detail="No transcript available. Please record some audio before ending the session.")
        
        # Generate title using LLaMA
        print(f"Generating title for lecture {lecture_id}...")
        
        title_prompt = f"""Based on the following lecture transcript, generate a concise and descriptive title (max 10 words) for this lecture. Return ONLY the title, do not share your thoughts or any other text.

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
        
        # Enhance transcript using OpenRouter (optional)
        enhanced_transcript = await enhance_transcript(generated_title, full_transcript)

        # Update lecture with title, transcript, enhancement, and end time
        update_payload = {
            "generated_title": generated_title,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "full_transcript": full_transcript,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if enhanced_transcript:
            update_payload["enhanced_full_transcript"] = enhanced_transcript

        update_response = supabase_client.table("lectures").update(
            update_payload
        ).eq("id", lecture_id).execute()
        
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

        all_transcriptions = transcriptions_response.data or []
        original_transcriptions = [item for item in all_transcriptions if not item.get("is_gpt_refined")]
        refined_transcriptions = [item for item in all_transcriptions if item.get("is_gpt_refined")]

        refined_full_transcript = " ".join([
            item.get("english_text", "") for item in refined_transcriptions if item.get("english_text")
        ]).strip()

        lecture_response.data["refined_full_transcript"] = refined_full_transcript
        
        return {
            "lecture": lecture_response.data,
            "transcriptions": original_transcriptions,
            "refined_transcriptions": refined_transcriptions,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Get lecture error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lecture: {error_msg}")


@app.post("/lecture/{lecture_id}/enhance")
async def enhance_lecture_transcript(lecture_id: int):
    """Regenerate and store enhanced transcript for a lecture"""
    try:
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not configured")
        if not openrouter_api_key:
            raise HTTPException(status_code=500, detail="OpenRouter API key not configured")

        lecture_response = supabase_client.table("lectures").select(
            "id, lecture_name, generated_title, full_transcript"
        ).eq("id", lecture_id).single().execute()

        if not lecture_response.data:
            raise HTTPException(status_code=404, detail="Lecture not found")

        lecture = lecture_response.data
        title = lecture.get("generated_title") or lecture.get("lecture_name") or "Untitled lecture"
        raw_transcript = lecture.get("full_transcript") or ""

        if not raw_transcript.strip():
            raise HTTPException(status_code=400, detail="No transcript available to enhance")

        enhanced_transcript = await enhance_transcript(title, raw_transcript)

        if not enhanced_transcript:
            raise HTTPException(status_code=500, detail="Enhancement failed")

        update_response = supabase_client.table("lectures").update({
            "enhanced_full_transcript": enhanced_transcript,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", lecture_id).execute()

        return {
            "lecture_id": lecture_id,
            "enhanced_full_transcript": enhanced_transcript,
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Enhance lecture error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to enhance transcript: {error_msg}")


@app.get("/lectures")
async def list_lectures():
    """List all lectures for history view"""
    try:
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not configured")

        response = supabase_client.table("lectures").select(
            "id, lecture_name, created_at, ended_at, generated_title, updated_at"
        ).order("created_at", desc=True).execute()

        return {
            "lectures": response.data or [],
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"List lectures error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to list lectures: {error_msg}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "groq_configured": groq_client is not None,
        "database_configured": supabase_client is not None,
        "openrouter_configured": openrouter_api_key is not None
    }


if __name__ == "__main__":
    import uvicorn
    print("\n🎙️  Urdu Audio Translator Starting...")
    print("📍 Open http://localhost:8000 in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
