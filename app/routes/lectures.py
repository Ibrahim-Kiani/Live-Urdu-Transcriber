"""Lecture management endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..clients import groq_client, openrouter_api_key, supabase_client
from ..config import TITLE_MODEL
from ..models import CreateLectureRequest, EndRecordingRequest, StartRecordingResponse
from ..services.transcription import enhance_transcript
from ..state import lectures_state

router = APIRouter()


@router.post("/lecture/create", response_model=StartRecordingResponse)
async def create_lecture(request: CreateLectureRequest):
    """Create a new lecture session"""
    try:
        if not supabase_client:
            raise HTTPException(
                status_code=500,
                detail="Database not configured. Please set SUPABASE_URL and SUPABASE_KEY"
            )

        response = supabase_client.table("lectures").insert({
            "lecture_name": request.lecture_name,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        if response.data:
            lecture_id = response.data[0]["id"]
            lectures_state[lecture_id] = {
                "lecture_name": request.lecture_name,
                "chunk_count": 0,
                "full_transcript": "",
                "raw_urdu_chunks": []
            }

            return StartRecordingResponse(
                lecture_id=lecture_id,
                lecture_name=request.lecture_name,
                status="success"
            )

        raise HTTPException(status_code=500, detail="Failed to create lecture")

    except Exception as e:
        error_msg = str(e)
        print(f"Lecture creation error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to create lecture: {error_msg}")


@router.post("/lecture/end")
async def end_recording(request: EndRecordingRequest):
    """End recording and generate title using LLaMA"""
    try:
        lecture_id = request.lecture_id

        print(f"🔚 Ending lecture {lecture_id}")

        if not groq_client:
            raise HTTPException(status_code=500, detail="Groq API not configured")

        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not configured")

        lecture_check = supabase_client.table("lectures").select(
            "id, ended_at"
        ).eq("id", lecture_id).single().execute()

        if not lecture_check.data:
            raise HTTPException(status_code=404, detail="Lecture not found in database")

        if lecture_check.data.get("ended_at"):
            raise HTTPException(status_code=400, detail="Lecture has already been ended")

        print(f"🔍 Fetching transcriptions from database for lecture {lecture_id}")
        transcript_response = supabase_client.table("transcriptions").select(
            "english_text"
        ).eq("lecture_id", lecture_id).eq("is_gpt_refined", False).order("chunk_number").execute()

        print(f"📝 Found {len(transcript_response.data) if transcript_response.data else 0} transcriptions in database")

        if not transcript_response.data:
            raise HTTPException(status_code=400, detail="No transcript available. Please record some audio before ending the session.")

        full_transcript = " ".join([
            item["english_text"] for item in transcript_response.data
        ])

        print(f"📄 Full transcript length: {len(full_transcript)} characters")
        print(f"📄 Transcript preview: {full_transcript[:200]}...")

        if not full_transcript.strip():
            raise HTTPException(status_code=400, detail="No transcript available. Please record some audio before ending the session.")

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

        enhanced_transcript = await enhance_transcript(generated_title, full_transcript)

        update_payload = {
            "generated_title": generated_title,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "full_transcript": full_transcript,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        if enhanced_transcript:
            update_payload["enhanced_full_transcript"] = enhanced_transcript

        supabase_client.table("lectures").update(
            update_payload
        ).eq("id", lecture_id).execute()

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


@router.get("/lecture/{lecture_id}/status")
async def check_lecture_status(lecture_id: int):
    """Check if a lecture session is still active"""
    try:
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not configured")

        lecture_response = supabase_client.table("lectures").select(
            "id, lecture_name, ended_at, generated_title"
        ).eq("id", lecture_id).single().execute()

        if not lecture_response.data:
            return {
                "exists": False,
                "active": False,
                "ended": False
            }

        lecture = lecture_response.data
        ended = lecture.get("ended_at") is not None

        return {
            "exists": True,
            "active": not ended,
            "ended": ended,
            "lecture_name": lecture.get("lecture_name"),
            "generated_title": lecture.get("generated_title")
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Check status error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to check status: {error_msg}")


@router.get("/lecture/{lecture_id}")
async def get_lecture(lecture_id: int):
    """Get lecture details and transcriptions"""
    try:
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not configured")

        lecture_response = supabase_client.table("lectures").select(
            "*"
        ).eq("id", lecture_id).single().execute()

        if not lecture_response.data:
            raise HTTPException(status_code=404, detail="Lecture not found")

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


@router.delete("/lecture/{lecture_id}/chunk/{chunk_number}")
async def delete_transcription_chunk(lecture_id: int, chunk_number: int):
    """Delete a specific chunk (original + refined) from a lecture"""
    try:
        if not supabase_client:
            raise HTTPException(status_code=500, detail="Database not configured")

        delete_response = supabase_client.table("transcriptions").delete().eq(
            "lecture_id", lecture_id
        ).eq("chunk_number", chunk_number).execute()

        if lecture_id in lectures_state:
            try:
                transcript_response = supabase_client.table("transcriptions").select(
                    "english_text"
                ).eq("lecture_id", lecture_id).eq("is_gpt_refined", False).order("chunk_number").execute()

                remaining = transcript_response.data or []
                lectures_state[lecture_id]["chunk_count"] = len(remaining)
                lectures_state[lecture_id]["full_transcript"] = " ".join(
                    [item.get("english_text", "") for item in remaining if item.get("english_text")]
                ).strip()
                raw_chunks = lectures_state[lecture_id].get("raw_urdu_chunks")
                if isinstance(raw_chunks, list) and 0 <= chunk_number < len(raw_chunks):
                    del raw_chunks[chunk_number]
            except Exception as state_error:
                print(f"⚠️  Failed to refresh lecture state after delete: {state_error}")

        return {
            "lecture_id": lecture_id,
            "chunk_number": chunk_number,
            "deleted": len(delete_response.data or []),
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Delete chunk error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to delete chunk: {error_msg}")


@router.post("/lecture/{lecture_id}/enhance")
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

        supabase_client.table("lectures").update({
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


@router.get("/lectures")
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
