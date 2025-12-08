-- 007_add_visualization_to_detection_results.sql
-- Migration: Add visualization columns to detection_results table

-- Add visualization storage columns
ALTER TABLE public.detection_results
ADD COLUMN IF NOT EXISTS annotated_image_url TEXT,
ADD COLUMN IF NOT EXISTS annotated_image_filename TEXT;

-- Add index for faster queries on images with visualizations
CREATE INDEX IF NOT EXISTS idx_detection_has_visualization 
ON public.detection_results (annotated_image_url) 
WHERE annotated_image_url IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN public.detection_results.annotated_image_url 
IS 'Public URL to annotated image with bounding boxes drawn';

COMMENT ON COLUMN public.detection_results.annotated_image_filename 
IS 'Storage filename in detection-visualizations bucket';
