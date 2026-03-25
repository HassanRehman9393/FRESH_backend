-- 011_create_ai_messages_table.sql
-- Migration: Create AI Messages table
-- Description: Separate table for AI conversation messages (normalized from ai_conversations)

-- ============================================================================
-- AI MESSAGES TABLE
-- Stores individual messages for AI assistant conversations
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.ai_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES public.ai_conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  tool_calls TEXT[],
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation ON public.ai_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_messages_created_at ON public.ai_messages(created_at);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================
ALTER TABLE public.ai_messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own conversation messages
CREATE POLICY "Users can view own conversation messages" ON public.ai_messages
  FOR SELECT
  USING (
    conversation_id IN (
      SELECT id FROM public.ai_conversations WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert into own conversations" ON public.ai_messages
  FOR INSERT
  WITH CHECK (
    conversation_id IN (
      SELECT id FROM public.ai_conversations WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete own conversation messages" ON public.ai_messages
  FOR DELETE
  USING (
    conversation_id IN (
      SELECT id FROM public.ai_conversations WHERE user_id = auth.uid()
    )
  );

-- ============================================================================
-- COMMENT
-- ============================================================================
COMMENT ON TABLE public.ai_messages IS 'Individual messages within AI assistant conversations';
