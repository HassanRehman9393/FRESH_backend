-- 015_update_export_standards_fruit_types.sql
-- Migration: Replace citrus with orange/grapefruit and add mango standards

-- Remove legacy citrus standards
DELETE FROM public.export_standards
WHERE fruit_type = 'citrus';

-- Insert/Upsert standards with updated fruit types
INSERT INTO public.export_standards (country, fruit_type, min_size_mm, max_defects_percent, pest_tolerance, disease_tolerance)
VALUES
('EU', 'mango', 60, 8, 'zero', 'low'),
('EU', 'orange', 45, 5, 'zero', 'low'),
('EU', 'grapefruit', 55, 5, 'zero', 'low'),
('EU', 'guava', 40, 8, 'zero', 'low'),

('UAE', 'mango', 65, 6, 'zero', 'low'),
('UAE', 'orange', 50, 3, 'zero', 'zero'),
('UAE', 'grapefruit', 58, 3, 'zero', 'zero'),
('UAE', 'guava', 45, 5, 'zero', 'low'),

('UK', 'mango', 58, 8, 'zero', 'low'),
('UK', 'orange', 45, 5, 'zero', 'low'),
('UK', 'grapefruit', 55, 5, 'zero', 'low'),
('UK', 'guava', 42, 7, 'zero', 'low'),

('Saudi Arabia', 'mango', 62, 7, 'zero', 'low'),
('Saudi Arabia', 'orange', 48, 4, 'zero', 'low'),
('Saudi Arabia', 'grapefruit', 56, 4, 'zero', 'low'),
('Saudi Arabia', 'guava', 44, 6, 'zero', 'low'),

('USA', 'mango', 65, 5, 'zero', 'zero'),
('USA', 'orange', 50, 2, 'zero', 'zero'),
('USA', 'grapefruit', 58, 2, 'zero', 'zero'),
('USA', 'guava', 45, 3, 'zero', 'zero')
ON CONFLICT (country, fruit_type)
DO UPDATE SET
  min_size_mm = EXCLUDED.min_size_mm,
  max_defects_percent = EXCLUDED.max_defects_percent,
  pest_tolerance = EXCLUDED.pest_tolerance,
  disease_tolerance = EXCLUDED.disease_tolerance;

-- Verification
SELECT country, fruit_type, min_size_mm, max_defects_percent
FROM public.export_standards
WHERE country IN ('EU', 'UAE', 'UK', 'Saudi Arabia', 'USA')
ORDER BY country, fruit_type;
