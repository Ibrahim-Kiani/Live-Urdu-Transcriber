"""HTML page routes."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from ..web import templates

router = APIRouter()

"""
@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    
    return templates.TemplateResponse("history.html", {"request": request})


@router.get("/live", response_class=HTMLResponse)
async def live(request: Request):
    
    return templates.TemplateResponse("index.html", {"request": request})
"""

@router.get("/", response_class=HTMLResponse)
async def landing_gemini(request: Request):
    """Serve the landing page"""
    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/history", response_class=HTMLResponse)
async def history_opus(request: Request):
    """Serve the lecture history page"""
    return templates.TemplateResponse("history.html", {"request": request})


@router.get("/live", response_class=HTMLResponse)
async def live_opus(request: Request):
    """Serve the live recording page"""
    return templates.TemplateResponse("index.html", {"request": request})
