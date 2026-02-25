-- Supabase SQL Schema for Urdu Transcriber

-- Create lectures table
CREATE TABLE lectures (
  id BIGSERIAL PRIMARY KEY,
  lecture_name TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  ended_at TIMESTAMP WITH TIME ZONE,
  generated_title TEXT,
  full_transcript TEXT,
  refined_full_transcript TEXT,
  enhanced_full_transcript TEXT,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create transcriptions table
CREATE TABLE transcriptions (
  id BIGSERIAL PRIMARY KEY,
  lecture_id BIGINT REFERENCES lectures(id) ON DELETE CASCADE,
  chunk_number INTEGER NOT NULL,
  urdu_audio_metadata TEXT,
  english_text TEXT NOT NULL,
  is_gpt_refined BOOLEAN NOT NULL DEFAULT FALSE,
  timestamps JSONB DEFAULT '{}'::jsonb,
  confidence_score FLOAT,
  processing_time_ms INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX idx_lectures_created_at ON lectures(created_at DESC);
CREATE INDEX idx_transcriptions_lecture_id ON transcriptions(lecture_id);
CREATE INDEX idx_transcriptions_created_at ON transcriptions(created_at DESC);

-- Enable RLS (Row Level Security) if needed
ALTER TABLE lectures ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcriptions ENABLE ROW LEVEL SECURITY;

-- Create policies for public access (modify as needed for your security requirements)
CREATE POLICY "Enable read access for all users" ON lectures
  FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON lectures
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all users" ON lectures
  FOR UPDATE USING (true);

CREATE POLICY "Enable read access for all users" ON transcriptions
  FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON transcriptions
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all users" ON transcriptions
  FOR UPDATE USING (true);
