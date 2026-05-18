-- Supabase Migration: Initial Schema
-- Creates tables for ontology management and conversation history

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========== Ontologies Table ==========
CREATE TABLE IF NOT EXISTS ontologies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    yaml_content TEXT NOT NULL,
    version TEXT DEFAULT '1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: Allow authenticated users to read, service role to write
ALTER TABLE ontologies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read for authenticated users" ON ontologies
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow insert/update/delete for service role" ON ontologies
    FOR ALL TO service_role USING (true);

-- ========== Conversations Table ==========
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ontology_id UUID REFERENCES ontologies(id) ON DELETE SET NULL,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read for authenticated users" ON conversations
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow insert/update/delete for service role" ON conversations
    FOR ALL TO service_role USING (true);

-- ========== Messages Table ==========
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    intent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read for authenticated users" ON messages
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow insert/update/delete for service role" ON messages
    FOR ALL TO service_role USING (true);

-- ========== Runs Table ==========
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'aborted', 'error')),
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

ALTER TABLE runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read for authenticated users" ON runs
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow insert/update/delete for service role" ON runs
    FOR ALL TO service_role USING (true);

-- ========== Indexes ==========
CREATE INDEX IF NOT EXISTS idx_conversations_ontology ON conversations(ontology_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_runs_conversation ON runs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_ontologies_created ON ontologies(created_at DESC);

-- ========== Updated_at Trigger Function ==========
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_ontologies_updated_at
    BEFORE UPDATE ON ontologies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
