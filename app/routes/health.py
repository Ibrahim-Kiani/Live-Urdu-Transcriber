"""Health check endpoint."""

from fastapi import APIRouter

from ..clients import groq_client, openrouter_api_key, supabase_client

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "groq_configured": groq_client is not None,
        "database_configured": supabase_client is not None,
        "openrouter_configured": openrouter_api_key is not None
    }
