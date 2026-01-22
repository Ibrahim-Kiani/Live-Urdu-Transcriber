# New Features: Lecture Sessions & Database Integration

Your Urdu Transcriber now has powerful new features for organizing and analyzing lectures!

## 🎯 New Features Overview

### 1. **Lecture Sessions**
- Users specify a **lecture name** before starting to record
- Session metadata is saved with clear timestamps
- Lecture name is displayed throughout the recording

### 2. **Database Storage (Supabase)**
- All transcriptions automatically saved to PostgreSQL
- Structured schema with relationships between lectures and chunks
- Easy retrieval and search capabilities

### 3. **AI-Generated Titles**
- After recording ends, **LLaMA model** analyzes the transcript
- Automatically generates a concise, descriptive title
- Stored alongside the lecture for easy identification

### 4. **Complete Transcription History**
- Every audio chunk stored with:
  - Chunk number/sequence
  - Translated English text
  - Timestamps (when created, processed)
  - Original lecture reference
- Full lecture transcript assembled and saved

## 📊 Database Schema

### `lectures` Table
```sql
CREATE TABLE lectures (
  id BIGSERIAL PRIMARY KEY,
  lecture_name TEXT NOT NULL,        -- User-provided name
  created_at TIMESTAMP,              -- Recording start time
  ended_at TIMESTAMP,                -- Recording end time
  generated_title TEXT,              -- AI-generated title
  full_transcript TEXT,              -- Complete transcript
  updated_at TIMESTAMP
);
```

**Example Record:**
```
id: 1
lecture_name: "Physics 101 - Quantum Mechanics"
created_at: 2026-01-22 10:15:00
ended_at: 2026-01-22 10:45:00
generated_title: "Quantum Mechanics Fundamentals"
full_transcript: "... full English text ..."
```

### `transcriptions` Table
```sql
CREATE TABLE transcriptions (
  id BIGSERIAL PRIMARY KEY,
  lecture_id BIGINT,                 -- FK to lectures
  chunk_number INTEGER,              -- Sequence (1, 2, 3...)
  english_text TEXT NOT NULL,        -- Translated text
  timestamps JSONB,                  -- {recorded_at: ...}
  confidence_score FLOAT,            -- Translation quality
  processing_time_ms INTEGER,        -- How long to process
  created_at TIMESTAMP
);
```

**Example Record:**
```
id: 1
lecture_id: 1
chunk_number: 1
english_text: "Today we'll discuss wave particle duality"
timestamps: {"recorded_at": "2026-01-22T10:15:05Z"}
created_at: 2026-01-22 10:15:05
```

## 🖥️ Frontend Changes

### Before Recording
```
┌─────────────────────────────────┐
│ Lecture/Session Name            │
│ [Enter lecture name here...] ◄──┤ NEW: User input
│                                 │
│ [Start Recording Session] ◄─────┤ NEW: Creates session
└─────────────────────────────────┘
```

### During Recording
```
┌─────────────────────────────────┐
│      [●] Recording Active       │
│      Tap to pause/resume        │
│ 📚 Physics 101 - Chapter 5 ◄────┤ NEW: Shows lecture name
│                                 │
│ Chunks: 5                       │
│                                 │
│ [End Session & Generate...] ◄───┤ NEW: Ends and generates title
└─────────────────────────────────┘
```

### After Recording
```
Success toast appears:
✅ Lecture saved! 
   Title: "Quantum Mechanics Fundamentals"
```

## 🔌 Backend API Endpoints

### POST `/lecture/create`
**Create a new lecture session**

Request:
```json
{
  "lecture_name": "Physics 101 - Chapter 5"
}
```

Response:
```json
{
  "lecture_id": 42,
  "lecture_name": "Physics 101 - Chapter 5",
  "status": "success"
}
```

### POST `/translate` (Enhanced)
**Translate audio and save to database**

Request (FormData):
```
audio: <audio blob>
lecture_id: 42
chunk_number: 1
```

Response:
```json
{
  "text": "Today we'll discuss wave particle duality",
  "status": "success",
  "lecture_id": 42,
  "chunk_number": 1
}
```

### POST `/lecture/end`
**End recording and generate title using LLaMA**

Request:
```json
{
  "lecture_id": 42
}
```

Response:
```json
{
  "lecture_id": 42,
  "generated_title": "Quantum Mechanics Fundamentals",
  "transcript_chunks": 12,
  "status": "success"
}
```

**The backend now:**
1. Retrieves all chunks for the lecture
2. Assembles full transcript
3. Sends to LLaMA model: `meta-llama/llama-4-scout-17b-16e-instruct`
4. LLaMA generates concise title
5. Saves title and final transcript to database

### GET `/lecture/{lecture_id}`
**Retrieve complete lecture with all transcriptions**

Response:
```json
{
  "lecture": {
    "id": 42,
    "lecture_name": "Physics 101 - Chapter 5",
    "generated_title": "Quantum Mechanics Fundamentals",
    "created_at": "2026-01-22T10:15:00Z",
    "ended_at": "2026-01-22T10:45:00Z",
    "full_transcript": "..."
  },
  "transcriptions": [
    {
      "chunk_number": 1,
      "english_text": "...",
      "created_at": "2026-01-22T10:15:05Z"
    },
    {
      "chunk_number": 2,
      "english_text": "...",
      "created_at": "2026-01-22T10:17:03Z"
    }
  ],
  "status": "success"
}
```

## 🚀 How It Works (Flow)

```
1. User opens app
   ↓
2. Enters lecture name
   ↓
3. Clicks "Start Recording Session"
   └─→ Backend: Creates record in 'lectures' table
   └─→ Frontend: Shows lecture name, recording controls
   ↓
4. User speaks (audio chunks auto-cut on silence)
   ↓
5. Each chunk sent to Groq Whisper
   └─→ Returns English translation
   └─→ Backend: Saves to 'transcriptions' table
   └─→ Frontend: Displays subtitle
   ↓
6. Repeat steps 4-5 for entire lecture
   ↓
7. User clicks "End Session & Generate Title"
   └─→ Backend: Assembles full transcript
   └─→ Calls Groq LLaMA model
   └─→ LLaMA returns: "Quantum Mechanics Fundamentals"
   └─→ Updates 'lectures' table with title
   └─→ Frontend: Shows success toast
   ↓
8. Lecture saved with title, transcript, timestamps!
```

## 📦 Dependencies Added

```txt
supabase==2.2.1         # Supabase client SDK
postgrest-py==0.13.3    # PostgreSQL REST client
```

## 🔧 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Supabase Account
See [SUPABASE_SETUP.md](SUPABASE_SETUP.md) for detailed steps

### 3. Create Database Schema
- Run SQL from `database_schema.sql` in Supabase SQL Editor

### 4. Add Environment Variables
```bash
# Copy .env.example to .env
GROQ_API_KEY=your_key_here
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...
```

### 5. Run Server
```bash
python main.py
```

Visit http://localhost:8000 and test!

## 💡 Use Cases

### 📚 Educational
- Teachers record lectures with automatic titles
- Students search lecture library
- Easy transcript search

### 📝 Meetings & Notes
- Record meeting name
- Auto-generate meeting summary title
- Full searchable transcript

### 🎤 Content Creation
- Podcast/webinar recording
- Auto-titled episodes
- Timestamped transcript
- Multi-language support (Urdu→English)

### 🔬 Research
- Structured data collection
- Detailed timestamps
- Easy analysis and export

## 📊 Example Workflow

**Recording a lecture:**
```
User: "Physics 101 - Chapter 5"
                   ↓
[Start Recording Session] clicked
                   ↓
User speaks in Urdu for 30 minutes
                   ↓
App generates 15 chunks with silences
Each chunk → Groq Whisper → English
Each chunk → Saved to database
                   ↓
[End Session & Generate Title] clicked
                   ↓
Full transcript assembled:
"Today we discuss wave particle duality...
The quantum realm behaves differently...
Photons act as both waves and particles..."
                   ↓
Sent to LLaMA: "Generate a title for this physics lecture"
                   ↓
LLaMA responds: "Wave-Particle Duality in Quantum Mechanics"
                   ↓
✅ Lecture saved with title and full transcript!
```

## 🔒 Data Privacy

- All data stored in **your Supabase account** (you control it)
- Database encrypted at rest and in transit
- Row-level security policies can be configured
- Easy to export or delete data

## 📈 Scaling

**Free tier supports:**
- 500 MB storage
- Reasonable concurrent users
- Perfect for personal/classroom use

**Pro tier ($25/month) supports:**
- 8 GB storage
- Higher rate limits
- Better performance

## 🐛 Debugging

Check your Supabase status:
```bash
# In browser console:
fetch('/health').then(r => r.json()).then(console.log)
```

Should show:
```json
{
  "status": "healthy",
  "groq_configured": true,
  "database_configured": true
}
```

## 📚 Further Reading

- [Supabase Docs](https://supabase.com/docs)
- [Groq API Docs](https://console.groq.com/docs)
- [LLaMA Model Card](https://huggingface.co/meta-llama)

---

**Questions?** Check the logs or re-read SUPABASE_SETUP.md! 🚀
