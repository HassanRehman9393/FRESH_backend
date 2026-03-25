-- 012_create_export_readiness_tables.sql
-- Migration: Create Export Readiness Module tables (Simplified)
-- Description: Essential tables for export standards, fruit grading, and compliance

-- ============================================================================
-- EXPORT STANDARDS TABLE
-- Country-specific standards for fruit export
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.export_standards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  country VARCHAR(50) NOT NULL,
  fruit_type VARCHAR(50) NOT NULL,
  min_size_mm INTEGER NOT NULL,
  max_defects_percent INTEGER NOT NULL CHECK (max_defects_percent BETWEEN 0 AND 100),
  pest_tolerance VARCHAR(20) NOT NULL CHECK (pest_tolerance IN ('zero', 'low', 'medium')),
  disease_tolerance VARCHAR(20) NOT NULL CHECK (disease_tolerance IN ('zero', 'low', 'medium')),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(country, fruit_type)
);

-- ============================================================================
-- FRUIT GRADES TABLE
-- Individual fruit grading results
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.fruit_grades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  orchard_id UUID REFERENCES public.orchards(id) ON DELETE CASCADE NOT NULL,
  fruit_type VARCHAR(50) NOT NULL,
  size_mm DECIMAL(5,1) NOT NULL,
  defect_count INTEGER NOT NULL DEFAULT 0,
  disease_detected VARCHAR(50),
  overall_grade DECIMAL(5,2) NOT NULL CHECK (overall_grade BETWEEN 0 AND 100),
  grade_category VARCHAR(20) NOT NULL CHECK (grade_category IN ('premium', 'grade_a', 'grade_b', 'reject')),
  target_market VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- COMPLIANCE CHECKS TABLE
-- Export compliance check history
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.compliance_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  orchard_id UUID REFERENCES public.orchards(id) ON DELETE CASCADE NOT NULL,
  target_market VARCHAR(50) NOT NULL,
  fruit_type VARCHAR(50) NOT NULL,
  compliance_status VARCHAR(20) NOT NULL CHECK (compliance_status IN ('compliant', 'non_compliant', 'conditional')),
  issues_found TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_export_standards_country ON public.export_standards(country);
CREATE INDEX IF NOT EXISTS idx_export_standards_fruit ON public.export_standards(fruit_type);

CREATE INDEX IF NOT EXISTS idx_fruit_grades_orchard ON public.fruit_grades(orchard_id);
CREATE INDEX IF NOT EXISTS idx_fruit_grades_category ON public.fruit_grades(grade_category);
CREATE INDEX IF NOT EXISTS idx_fruit_grades_created ON public.fruit_grades(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_compliance_checks_orchard ON public.compliance_checks(orchard_id);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_market ON public.compliance_checks(target_market);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_created ON public.compliance_checks(created_at DESC);

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE public.export_standards IS 'Country-specific export standards for fruits';
COMMENT ON TABLE public.fruit_grades IS 'Individual fruit grading results';
COMMENT ON TABLE public.compliance_checks IS 'Export compliance check history';
