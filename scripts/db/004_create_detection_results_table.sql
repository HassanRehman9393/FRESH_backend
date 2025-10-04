-- 004_create_detection_results_table.sql
-- Migration: Create detection_results table for FRESH Backend API

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.detection_results (
  detection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  image_id UUID NOT NULL REFERENCES public.images(id) ON DELETE CASCADE,
  fruit_type TEXT,
  confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  bounding_box JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_detection_results_image_id ON public.detection_results (image_id);
CREATE INDEX IF NOT EXISTS idx_detection_results_user_id ON public.detection_results (user_id);
CREATE INDEX IF NOT EXISTS idx_detection_results_fruit_type ON public.detection_results (fruit_type);
