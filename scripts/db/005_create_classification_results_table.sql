-- 005_create_classification_results_table.sql
-- Migration: Create classification_results table for FRESH Backend API

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.classification_results (
  classification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  detection_id UUID NOT NULL REFERENCES public.detection_results(detection_id) ON DELETE CASCADE,
  ripeness_level VARCHAR(16) NOT NULL CHECK (ripeness_level IN ('ripe','unripe','overripe','rotten')),
  confidence_score NUMERIC(5,4) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
  estimated_color TEXT,
  estimated_size TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_classification_results_detection_id ON public.classification_results (detection_id);
CREATE INDEX IF NOT EXISTS idx_classification_results_ripeness_level ON public.classification_results (ripeness_level);
