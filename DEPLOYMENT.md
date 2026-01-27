# Deployment Guide

## Vercel Deployment (Recommended)

This project is configured to deploy to Vercel using `vercel.json` and the Python runtime.

### Prerequisites
- GitHub repository with your code pushed
- Vercel account (free at https://vercel.com)
- Groq API key (free at https://console.groq.com)

### 1. Push Your Code to GitHub

```bash
cd d:\transcribe\Live-Urdu-Transcriber
git add .
git commit -m "Add Vercel deployment config"
git push
```

### 2. Import Project in Vercel

1. Go to https://vercel.com
2. Click **Add New** → **Project**
3. Import your GitHub repository
4. Framework preset: **Other**
5. Root Directory: **leave empty**

### 3. Configure Environment Variables

Add the following Environment Variables in Vercel:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | Your Groq API key |
| `OPENROUTER_API_KEY` | (Optional) OpenRouter key for transcript enhancement |
| `SUPABASE_URL` | (Optional) Supabase URL |
| `SUPABASE_KEY` | (Optional) Supabase service key |

### 4. Deploy

Click **Deploy**. Vercel will:
- Install dependencies from `requirements.txt`
- Build the Python serverless function at `api/index.py`
- Route all requests to the FastAPI app

### 5. Verify

Open your deployed URL and visit:
- `/` for the UI
- `/health` for configuration status

### Files Added for Vercel

- `api/index.py` → Vercel entrypoint exporting the FastAPI `app`
- `vercel.json` → Build + routing config

---

# Render Deployment Guide

## Quick Start

This project is configured to deploy to Render using `render.yaml`.

### Prerequisites
- GitHub repository with your code pushed
- Render account (free at [render.com](https://render.com))
- Groq API key (free at [console.groq.com](https://console.groq.com))

## Deployment Steps

### 1. Push Your Code to GitHub

```bash
cd d:\urdu-transcription
git add .
git commit -m "Deployment-ready: Add render.yaml and dependencies"
git push -u origin master
```

### 2. Connect to Render

1. Go to https://render.com
2. Click **New +** → **Web Service**
3. Select **Connect a repository**
4. Find and select your `urdu-transcription` repository
5. Click **Connect**

### 3. Configure the Service

Fill in the form:

| Field | Value |
|-------|-------|
| **Name** | `urdu-translator` |
| **Root Directory** | (leave empty) |
| **Runtime** | `Python 3.11` |
| **Build Command** | (leave empty - uses render.yaml) |
| **Start Command** | (leave empty - uses render.yaml) |
| **Plan** | `Free` (or Starter for better performance) |

### 4. Add Environment Variables

Click **Add Environment Variable**:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | Your Groq API key (get from https://console.groq.com) |


⚠️ **Important**: Your GROQ_API_KEY will be kept secure and not exposed publicly.

### 5. Deploy

Click **Create Web Service**

Render will:
- Read `render.yaml` configuration automatically
- Install Python packages from `requirements.txt`
- Start the FastAPI server
- Provide your live URL

### 6. Access Your App

Your app will be live in ~2-3 minutes at:
```
https://urdu-translator.onrender.com
```

(Render generates a unique URL for your service)

## File Breakdown

### `render.yaml`
- Specifies Python 3.11 runtime
- Configures build command: `pip install -r requirements.txt`
- Configures start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Sets up environment variables

### `requirements.txt`
All Python dependencies needed:
- fastapi
- uvicorn
- groq
- python-dotenv
- python-multipart
- jinja2

### `main.py`
FastAPI backend that:
- Serves the HTML UI
- Handles `/translate` endpoint
- Communicates with Groq API
- Returns translations

### `templates/index.html`
Frontend with:
- Microphone recording via Web Audio API
- Silence detection logic
- Real-time subtitle display

## Monitoring Your Deployment

### View Logs
1. Go to your Render dashboard
2. Click on your service
3. View **Logs** tab

### Common Issues

**Service fails to deploy:**
- Check logs for error messages
- Verify Python version compatibility
- Ensure requirements.txt syntax is correct

**API returns 401 error:**
- Verify GROQ_API_KEY is set in Environment Variables
- Check API key is valid at console.groq.com

**"Service unavailable" message:**
- Render free tier restarts after 15 minutes of inactivity
- Keep your app active or upgrade to Starter plan

## Updating Your App

After making changes locally:

```bash
git add .
git commit -m "Update feature XYZ"
git push
```

Render will **automatically redeploy** your service! 🚀

## Scaling & Performance

- **Free Plan**: Supports small-to-medium traffic, restarts after inactivity
- **Starter Plan** ($7/month): Keeps service always-on, better for production
- Add more services for horizontal scaling as needed

## Cost

- **Free tier**: $0 (but restarts after inactivity)
- **Starter+**: $7/month per service (recommended)
- **Groq API**: Generous free tier for Whisper translations

## Support

For Render-specific help:
- https://render.com/docs
- https://render.com/support

For app-specific issues:
- Check project README.md
- Review browser console (F12)
- Check Render service logs

---

**Your Urdu Translator is now deployed!** 🎉
