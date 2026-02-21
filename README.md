# **Fast Lecture Transcription Service**

A mobile-responsive web application that records live audio from the user's microphone, detects speech pauses (silence), sends audio chunks to a backend, and returns English subtitles translated from Urdu using Groq's Whisper API.

## Features

✨ **Real-time Translation**
- Records audio from microphone
- Automatically detects speech pauses (0.8-1.2 seconds of silence)
- Sends audio chunks to backend for translation
- Displays English subtitles in real-time

🎯 **Smart Silence Detection**
- Uses Web Audio API to monitor microphone volume (RMS)
- Filters background noise and ambient sound
- Requires minimum peak volume to accept audio
- Prevents false triggers

📱 **Mobile-First Design**
- Fully responsive UI with Tailwind CSS
- Works on mobile browsers
- Touch-optimized controls

🚀 **High Performance**
- Frontend handles audio recording and silence detection (saves bandwidth)
- Backend processes translations via Groq Whisper API
- Seamless chunk handoff (no words lost during upload)

## Tech Stack

- **Backend**: Python FastAPI, Groq API (Whisper Large V3)
- **Frontend**: HTML5, JavaScript (Vanilla), Tailwind CSS
- **Audio**: Web Audio API, MediaRecorder API
- **Deployment**: Render, Docker-ready

##  Setup

### Prerequisites
- Python 3.9+
- A Groq API key (free at [console.groq.com](https://console.groq.com))
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Ibrahim-Kiani/FAST-Lecture-Transcription-Service.git
   cd urdu-transcription
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env and add your GROQ_API_KEY
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server**
   ```bash
   python main.py
   ```

5. **Open in browser**
   - Navigate to `http://localhost:8000`

## Deployment to Render

### Step 1: Prepare Your GitHub Repository
```bash
git add .
git commit -m "Ready for deployment"
git push
```

## Configuration

Edit these settings in `templates/index.html`:

```javascript
const CONFIG = {
    SILENCE_THRESHOLD: 0.10,       // Volume threshold (0-1)
    SILENCE_DURATION: 1500,        // ms before cutting
    MAX_CHUNK_DURATION: 10000,     // Max 10 seconds per chunk
    MIN_CHUNK_BYTES: 12000,        // Minimum audio size (12KB)
    MIN_PEAK_VOLUME: 0.15,         // Minimum peak volume to accept
};
```

## API Endpoints

### GET `/`
Serves the web application UI.

### POST `/translate`
Translates audio from Urdu to English.

**Request:**
- Body: `multipart/form-data` with `audio` file

**Response:**
```json
{
    "text": "Translated English text",
    "status": "success"
}
```

### GET `/health`
Health check endpoint.

## Troubleshooting

### "Thank you" keeps getting spammed
- Increase `SILENCE_THRESHOLD` to 0.10+
- Increase `MIN_PEAK_VOLUME` to 0.15+
- Increase `MIN_CHUNK_BYTES` to 12000+

### Microphone not detected
- Allow microphone access in browser
- Check if another app is using the microphone
- Try a different browser

### API returns 401 error
- Check that `GROQ_API_KEY` is set correctly in environment
- Verify API key hasn't expired

### No translations appearing
- Check browser console for JavaScript errors (F12)
- Verify backend is running with `python main.py`
- Check network tab for API response errors

## File Structure

```
urdu-transcription/
├── main.py                 # FastAPI server
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment config
├── .env.example           # Environment template
├── .gitignore            # Git ignore rules
├── README.md             # This file
└── templates/
    └── index.html        # Web UI + JavaScript
```

## License

MIT

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review browser console errors (F12)
3. Check Render deployment logs
4. Open a GitHub issue

---

**Made with ❤️ for real-time Urdu to English translation**
