-- 006_create_disease_detections_table.sql
-- Migration: Create disease_detections table for FRESH Backend API

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.disease_detections (
  disease_detection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  detection_id UUID NOT NULL REFERENCES public.detection_results(detection_id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  image_id UUID NOT NULL REFERENCES public.images(id) ON DELETE CASCADE,
  disease_type VARCHAR(32) NOT NULL CHECK (disease_type IN ('healthy','anthracnose','citrus_canker','unknown')),
  is_diseased BOOLEAN NOT NULL DEFAULT false,
  disease_confidence NUMERIC(5,4) NOT NULL CHECK (disease_confidence >= 0 AND disease_confidence <= 1),
  severity_level VARCHAR(16) CHECK (severity_level IN ('mild','moderate','severe','critical')),
  probabilities JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_disease_detections_detection_id ON public.disease_detections (detection_id);
CREATE INDEX IF NOT EXISTS idx_disease_detections_user_id ON public.disease_detections (user_id);
CREATE INDEX IF NOT EXISTS idx_disease_detections_image_id ON public.disease_detections (image_id);
CREATE INDEX IF NOT EXISTS idx_disease_detections_disease_type ON public.disease_detections (disease_type);
CREATE INDEX IF NOT EXISTS idx_disease_detections_is_diseased ON public.disease_detections (is_diseased);
