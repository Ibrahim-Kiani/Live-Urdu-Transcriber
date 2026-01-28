"""Pydantic request/response models."""

from typing import Optional
from pydantic import BaseModel


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
