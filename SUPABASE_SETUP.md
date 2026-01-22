# Supabase Setup Guide

This guide will help you set up the Supabase PostgreSQL database for storing lectures and transcriptions.

## Step 1: Create a Supabase Account

1. Go to [supabase.com](https://supabase.com)
2. Click **Sign Up**
3. Create an account using GitHub or email

## Step 2: Create a New Project

1. Click **New Project**
2. Fill in:
   - **Project name**: `urdu-transcriber` (or your choice)
   - **Database password**: Create a strong password (save it!)
   - **Region**: Choose closest to your location
3. Click **Create new project**

⏳ *Wait 2-3 minutes for the database to initialize*

## Step 3: Get Your Credentials

1. Once created, go to **Project Settings** (⚙️ icon)
2. Click **API** in the left sidebar
3. Copy these values:
   - **Project URL** → This is your `SUPABASE_URL`
   - **Project API Key** (anon/public) → This is your `SUPABASE_KEY`

4. Add to your `.env` file:
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...
   ```

## Step 4: Create Database Tables

1. Go to **SQL Editor** in the Supabase dashboard
2. Click **New Query**
3. Copy and paste the entire contents from `database_schema.sql`
4. Click **Run** (or press Cmd+Enter)

You should see:
```
Query successful (no rows)
```

## Step 5: Verify Tables Were Created

1. Go to **Table Editor** in the left sidebar
2. You should see two tables:
   - `lectures` - Stores lecture sessions with metadata
   - `transcriptions` - Stores individual audio chunks and translations

### Table: `lectures`
```
Columns:
- id (int) - Primary key
- lecture_name (text) - Session name
- created_at (timestamp) - When recording started
- ended_at (timestamp) - When recording ended
- generated_title (text) - AI-generated title
- full_transcript (text) - Complete transcript
- updated_at (timestamp) - Last update time
```

### Table: `transcriptions`
```
Columns:
- id (int) - Primary key
- lecture_id (int) - FK to lectures
- chunk_number (int) - Sequence number
- english_text (text) - Translated text
- timestamps (jsonb) - Metadata timestamps
- confidence_score (float) - Translation confidence
- processing_time_ms (int) - Time to process
- created_at (timestamp) - When created
- updated_at (timestamp) - Last update
```

## Step 6: Test the Connection

Run your app:
```bash
python main.py
```

You should see:
```
✅ Connected to Supabase
```

## Step 7: Test Recording a Lecture

1. Open http://localhost:8000
2. Enter a lecture name: "Test Lecture"
3. Click **Start Recording Session**
4. Speak some Urdu text
5. The transcriptions should be saved to your database in real-time
6. Click **End Session & Generate Title** to finalize

## Viewing Your Data

### View Lectures
1. Go to Supabase dashboard
2. **Table Editor** → **lectures**
3. You'll see all your recorded lectures with:
   - Generated titles
   - Full transcripts
   - Recording timestamps

### View Transcriptions
1. **Table Editor** → **transcriptions**
2. Each row is one audio chunk with:
   - The lecture it belongs to
   - The translated English text
   - When it was processed

## Troubleshooting

### "Database not configured" error
- Check that `SUPABASE_URL` and `SUPABASE_KEY` are in your `.env` file
- Restart the server after adding `.env` variables
- Verify credentials in Supabase dashboard

### "Table does not exist" error
- Make sure you ran the SQL schema (Step 4)
- Check **Table Editor** to confirm tables exist
- Re-run the SQL query if needed

### "Connection refused" error
- Verify internet connection
- Check that your Supabase project is active (not paused)
- Try creating a new project if issues persist

### Slow uploads
- Supabase free tier is rate-limited
- Consider upgrading to Pro ($25/mo) for production
- Add request batching if needed

## Data Retention & Privacy

- **Free tier**: 500MB storage
- **Pro tier**: 8GB storage (can increase)
- All data is encrypted at rest and in transit
- You control all data - no third party access

## Backing Up Data

To export your data:

1. Go to **SQL Editor**
2. Run:
   ```sql
   -- Export all lectures
   SELECT * FROM lectures ORDER BY created_at DESC;
   
   -- Export all transcriptions
   SELECT * FROM transcriptions ORDER BY created_at DESC;
   ```
3. Download as CSV using the "Export" button

## Scaling & Performance

For production, consider:

1. **Enable pgBouncer** (Supabase → Project Settings → Database)
   - Better connection pooling
   - Reduces latency

2. **Add database indexes** (auto-created by schema.sql):
   ```sql
   CREATE INDEX idx_lectures_created_at ON lectures(created_at DESC);
   CREATE INDEX idx_transcriptions_lecture_id ON transcriptions(lecture_id);
   ```

3. **Upgrade to Pro tier** ($25/month):
   - More concurrent connections
   - Higher rate limits
   - 8GB storage instead of 500MB

## API Documentation

Your app uses these Supabase endpoints internally:

- `POST /lecture/create` - Create new lecture session
- `POST /translate` - Save translation chunk
- `POST /lecture/end` - Finalize and generate title
- `GET /lecture/{id}` - Retrieve lecture data

No manual API calls needed - the app handles everything!

---

**Need help?**
- [Supabase Docs](https://supabase.com/docs)
- [Supabase Community](https://discord.supabase.io)
- Check server logs: `python main.py`
