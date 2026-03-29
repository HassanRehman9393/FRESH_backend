-- 014_create_export_documents_table.sql
-- Migration: Create Export Documentation table for generated export CSV reports

CREATE TABLE IF NOT EXISTS public.export_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  orchard_id UUID REFERENCES public.orchards(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
  document_type VARCHAR(40) NOT NULL CHECK (document_type IN ('grade_report', 'compliance_report', 'readiness_summary')),
  target_market VARCHAR(50) NOT NULL,
  fruit_type VARCHAR(50),
  file_name VARCHAR(255) NOT NULL,
  file_size_bytes INTEGER NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed')),
  date_from DATE,
  date_to DATE,
  generated_content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_export_documents_user ON public.export_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_export_documents_orchard ON public.export_documents(orchard_id);
CREATE INDEX IF NOT EXISTS idx_export_documents_created ON public.export_documents(created_at DESC);

COMMENT ON TABLE public.export_documents IS 'Generated export documentation files metadata and content';
