"""FastAPI application setup."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, lectures, pages, translate

app = FastAPI(
    title="Urdu Audio Translator",
    description="Real-time Urdu to English audio translation with LLaMA title generation",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pages.router)
app.include_router(translate.router)
app.include_router(lectures.router)
app.include_router(health.router)
