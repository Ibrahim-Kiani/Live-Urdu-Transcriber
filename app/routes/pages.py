"""HTML page routes."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from ..web import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the lecture history page as the landing page"""
    return templates.TemplateResponse("history.html", {"request": request})


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    """Serve the lecture history page"""
    return templates.TemplateResponse("history.html", {"request": request})


@router.get("/live", response_class=HTMLResponse)
async def live(request: Request):
    """Serve the live recording page"""
    return templates.TemplateResponse("index.html", {"request": request})
