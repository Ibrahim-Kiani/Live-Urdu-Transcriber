"""Audio translation endpoints."""

import os
import tempfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..clients import groq_client, supabase_client
from ..config import TRANSLATION_MODEL, TRANSCRIPTION_MODEL
from ..models import TranslationResponse
from ..services.audio_processing import prepare_audio
from ..services.transcription import refine_urdu_transcript
from ..state import lectures_state

router = APIRouter()


@router.post("/translate")
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
    lecture_id_int = int(lecture_id) if lecture_id else None
    chunk_number_int = int(chunk_number) if chunk_number else None

    print(f"📝 Translation request - lecture_id: {lecture_id_int}, chunk_number: {chunk_number_int}")

    if not groq_client:
        raise HTTPException(
            status_code=500,
            detail="Groq API key not configured. Please set GROQ_API_KEY in .env file"
        )

    content_type = audio.content_type or "audio/wav"
    if not any(t in content_type for t in ["audio/wav", "audio/x-wav", "audio/wave", "audio"]):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {content_type}. Expected audio file."
        )

    try:
        audio_content = await audio.read()

        if len(audio_content) < 5000:
            return {"text": "", "status": "too_short"}

        if "wav" not in content_type:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {content_type}. Expected WAV audio."
            )

        prepared_audio = prepare_audio(audio_content, input_format="wav", compressor_ratio=4.0)

        if not prepared_audio or len(prepared_audio) < 5000:
            return {"text": "", "status": "too_short"}

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(prepared_audio)
            temp_file_path = temp_file.name

        try:
            with open(temp_file_path, "rb") as audio_file:
                translation = groq_client.audio.translations.create(
                    model=TRANSLATION_MODEL,
                    file=audio_file,
                    response_format="text"
                )

            translated_text = str(translation).strip()

            with open(temp_file_path, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    model=TRANSCRIPTION_MODEL,
                    file=audio_file,
                    response_format="text"
                )

            urdu_transcript = str(transcription).strip()
            refined_text = refine_urdu_transcript(urdu_transcript) if urdu_transcript else None

            print(f"✅ Translated: {translated_text[:100]}...")

            response_status = "success"
            response_lecture_id = lecture_id_int
            response_chunk_number = chunk_number_int
            skip_save_reason = None
            actual_chunk_number = chunk_number_int

            if lecture_id_int and supabase_client and translated_text:
                try:
                    lecture_check = supabase_client.table("lectures").select(
                        "id, ended_at"
                    ).eq("id", lecture_id_int).single().execute()

                    if not lecture_check.data:
                        print(f"⚠️  Lecture {lecture_id_int} not found in database, skipping save")
                        skip_save_reason = "lecture_missing"
                    elif lecture_check.data.get("ended_at"):
                        print(f"⚠️  Lecture {lecture_id_int} already ended, skipping save")
                        skip_save_reason = "lecture_ended"
                    else:
                        if actual_chunk_number is None:
                            chunk_count_query = supabase_client.table("transcriptions").select(
                                "chunk_number"
                            ).eq("lecture_id", lecture_id_int).eq("is_gpt_refined", False).execute()

                            actual_chunk_number = len(chunk_count_query.data) if chunk_count_query.data else 0

                        print(f"💾 Saving to database - lecture_id: {lecture_id_int}, chunk: {actual_chunk_number}")

                        result = supabase_client.table("transcriptions").insert({
                            "lecture_id": lecture_id_int,
                            "chunk_number": actual_chunk_number,
                            "english_text": translated_text,
                            "is_gpt_refined": False,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "timestamps": {
                                "recorded_at": datetime.now(timezone.utc).isoformat()
                            }
                        }).execute()

                        print(f"✅ Saved to database successfully: {result.data}")

                        if lecture_id_int in lectures_state:
                            existing_count = lectures_state[lecture_id_int].get("chunk_count", 0)
                            lectures_state[lecture_id_int]["chunk_count"] = max(
                                existing_count,
                                (actual_chunk_number or 0) + 1
                            )
                            lectures_state[lecture_id_int]["full_transcript"] += " " + translated_text
                            print(f"📊 Updated state - chunks: {lectures_state[lecture_id_int]['chunk_count']}")

                        if refined_text:
                            try:
                                supabase_client.table("transcriptions").insert({
                                    "lecture_id": lecture_id_int,
                                    "chunk_number": actual_chunk_number,
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

                except Exception as db_error:
                    print(f"❌ Database save error: {db_error}")
                    import traceback
                    traceback.print_exc()
            else:
                if not lecture_id_int:
                    print("⚠️  No lecture_id provided, skipping database save")

            if skip_save_reason == "lecture_missing":
                response_status = "success_no_save"
                response_lecture_id = None
                response_chunk_number = None
            elif skip_save_reason == "lecture_ended":
                response_status = "lecture_ended"
                response_lecture_id = None
                response_chunk_number = None
            else:
                response_chunk_number = actual_chunk_number

            return TranslationResponse(
                text=translated_text,
                refined_text=refined_text,
                status=response_status,
                lecture_id=response_lecture_id,
                chunk_number=response_chunk_number
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
