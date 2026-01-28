"""App entrypoint for local development."""

from app.app import app


if __name__ == "__main__":
    import uvicorn
    print("\n🎙️  Urdu Audio Translator Starting...")
    print("📍 Open http://localhost:8000 in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
