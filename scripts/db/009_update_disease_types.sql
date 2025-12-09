-- 009_update_disease_types.sql
-- Migration: Update disease_detections table to support all disease types

-- Drop the old constraint
ALTER TABLE public.disease_detections 
DROP CONSTRAINT IF EXISTS disease_detections_disease_type_check;

-- Add the new constraint with all disease types
ALTER TABLE public.disease_detections 
ADD CONSTRAINT disease_detections_disease_type_check 
CHECK (disease_type IN ('healthy','anthracnose','citrus_canker','blackspot','fruitfly','unknown'));
