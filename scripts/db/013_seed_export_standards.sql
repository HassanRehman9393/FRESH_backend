-- 013_seed_export_standards.sql
-- Seed initial export standards for major markets (Simplified)

-- ============================================================================
-- EU STANDARDS
-- ============================================================================
INSERT INTO public.export_standards (country, fruit_type, min_size_mm, max_defects_percent, pest_tolerance, disease_tolerance)
VALUES 
('EU', 'mango', 60, 8, 'zero', 'low'),
('EU', 'orange', 45, 5, 'zero', 'low'),
('EU', 'grapefruit', 55, 5, 'zero', 'low'),
('EU', 'guava', 40, 8, 'zero', 'low');

-- ============================================================================
-- UAE STANDARDS
-- ============================================================================
INSERT INTO public.export_standards (country, fruit_type, min_size_mm, max_defects_percent, pest_tolerance, disease_tolerance)
VALUES 
('UAE', 'mango', 65, 6, 'zero', 'low'),
('UAE', 'orange', 50, 3, 'zero', 'zero'),
('UAE', 'grapefruit', 58, 3, 'zero', 'zero'),
('UAE', 'guava', 45, 5, 'zero', 'low');

-- ============================================================================
-- UK STANDARDS
-- ============================================================================
INSERT INTO public.export_standards (country, fruit_type, min_size_mm, max_defects_percent, pest_tolerance, disease_tolerance)
VALUES 
('UK', 'mango', 58, 8, 'zero', 'low'),
('UK', 'orange', 45, 5, 'zero', 'low'),
('UK', 'grapefruit', 55, 5, 'zero', 'low'),
('UK', 'guava', 42, 7, 'zero', 'low');

-- ============================================================================
-- SAUDI ARABIA STANDARDS
-- ============================================================================
INSERT INTO public.export_standards (country, fruit_type, min_size_mm, max_defects_percent, pest_tolerance, disease_tolerance)
VALUES 
('Saudi Arabia', 'mango', 62, 7, 'zero', 'low'),
('Saudi Arabia', 'orange', 48, 4, 'zero', 'low'),
('Saudi Arabia', 'grapefruit', 56, 4, 'zero', 'low'),
('Saudi Arabia', 'guava', 44, 6, 'zero', 'low');

-- ============================================================================
-- USA STANDARDS
-- ============================================================================
INSERT INTO public.export_standards (country, fruit_type, min_size_mm, max_defects_percent, pest_tolerance, disease_tolerance)
VALUES 
('USA', 'mango', 65, 5, 'zero', 'zero'),
('USA', 'orange', 50, 2, 'zero', 'zero'),
('USA', 'grapefruit', 58, 2, 'zero', 'zero'),
('USA', 'guava', 45, 3, 'zero', 'zero');

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT country_name, fruit_type, min_size_mm, max_defects_percent 
FROM public.export_standards 
ORDER BY country, fruit_type;
