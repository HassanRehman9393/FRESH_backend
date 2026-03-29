-- 010_create_ai_assistant_tables.sql
-- Migration: Create AI Assistant knowledge base tables
-- Description: Tables for diseases, treatments, MRL limits, export requirements,
--              fruit varieties, and AI conversation history

-- ============================================================================
-- DISEASES TABLE
-- Stores comprehensive disease information for AI assistant queries
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.diseases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  name_urdu TEXT,
  disease_type TEXT CHECK (disease_type IN ('fungal', 'bacterial', 'viral', 'pest', 'nutritional')),
  affected_fruits TEXT[] NOT NULL,
  symptoms TEXT[] NOT NULL,
  causes TEXT,
  prevention TEXT[],
  images TEXT[],
  severity_levels JSONB,
  spread_conditions TEXT,
  detection_methods TEXT[],
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- TREATMENTS TABLE
-- Stores treatment options linked to diseases
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.treatments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  disease_id UUID REFERENCES public.diseases(id) ON DELETE CASCADE,
  treatment_type TEXT NOT NULL CHECK (treatment_type IN ('chemical', 'organic', 'cultural', 'biological')),
  product_name TEXT NOT NULL,
  product_name_urdu TEXT,
  active_ingredient TEXT,
  concentration TEXT,
  dosage TEXT NOT NULL,
  application_method TEXT,
  application_timing TEXT,
  frequency TEXT,
  pre_harvest_interval_days INT,
  re_entry_interval_hours INT,
  safety_precautions TEXT[],
  effectiveness_rating INT CHECK (effectiveness_rating BETWEEN 1 AND 5),
  cost_category TEXT CHECK (cost_category IN ('low', 'medium', 'high')),
  availability_pakistan BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- MRL LIMITS TABLE
-- Maximum Residue Limits by country for export compliance
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.mrl_limits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pesticide_name TEXT NOT NULL,
  active_ingredient TEXT NOT NULL,
  fruit_type TEXT NOT NULL,
  country_code TEXT NOT NULL,
  country_name TEXT NOT NULL,
  mrl_value DECIMAL(10,4) NOT NULL,
  unit TEXT DEFAULT 'mg/kg',
  source TEXT,
  regulation_reference TEXT,
  last_updated DATE,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(pesticide_name, fruit_type, country_code)
);

-- ============================================================================
-- EXPORT REQUIREMENTS TABLE
-- Country-specific export requirements for fruits
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.export_requirements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  country_code TEXT NOT NULL,
  country_name TEXT NOT NULL,
  fruit_type TEXT NOT NULL,
  phytosanitary_requirements TEXT[],
  pest_free_requirements TEXT[],
  packaging_standards TEXT[],
  labeling_requirements TEXT[],
  documentation_required TEXT[],
  temperature_requirements JSONB,
  humidity_requirements JSONB,
  shelf_life_days INT,
  certifications_needed TEXT[],
  import_restrictions TEXT[],
  port_of_entry TEXT[],
  inspection_requirements TEXT[],
  quarantine_treatment TEXT,
  season_restrictions TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(country_code, fruit_type)
);

-- ============================================================================
-- FRUIT VARIETIES TABLE
-- Pakistani fruit varieties and their characteristics
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.fruit_varieties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fruit_type TEXT NOT NULL,
  variety_name TEXT NOT NULL,
  variety_name_urdu TEXT,
  region TEXT,
  harvest_season TEXT,
  harvest_months INT[],
  export_grade_criteria JSONB,
  quality_parameters JSONB,
  common_diseases TEXT[],
  storage_requirements JSONB,
  shelf_life_days INT,
  export_popularity TEXT CHECK (export_popularity IN ('high', 'medium', 'low')),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(fruit_type, variety_name)
);

-- ============================================================================
-- AI CONVERSATIONS TABLE
-- Stores conversation history for the AI assistant
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.ai_conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
  session_id TEXT,
  title TEXT,
  messages JSONB[] DEFAULT ARRAY[]::JSONB[],
  context JSONB,
  language TEXT DEFAULT 'en' CHECK (language IN ('en', 'ur', 'mixed')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================================
-- FARMING CALENDAR TABLE
-- Seasonal farming activities and recommendations
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.farming_calendar (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fruit_type TEXT NOT NULL,
  month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
  activities TEXT[] NOT NULL,
  disease_risks TEXT[],
  recommended_treatments TEXT[],
  weather_considerations TEXT[],
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(fruit_type, month)
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_diseases_name ON public.diseases(name);
CREATE INDEX IF NOT EXISTS idx_diseases_affected_fruits ON public.diseases USING GIN(affected_fruits);
CREATE INDEX IF NOT EXISTS idx_treatments_disease ON public.treatments(disease_id);
CREATE INDEX IF NOT EXISTS idx_treatments_type ON public.treatments(treatment_type);
CREATE INDEX IF NOT EXISTS idx_mrl_country ON public.mrl_limits(country_code);
CREATE INDEX IF NOT EXISTS idx_mrl_fruit ON public.mrl_limits(fruit_type);
CREATE INDEX IF NOT EXISTS idx_mrl_pesticide ON public.mrl_limits(pesticide_name);
CREATE INDEX IF NOT EXISTS idx_export_country ON public.export_requirements(country_code);
CREATE INDEX IF NOT EXISTS idx_export_fruit ON public.export_requirements(fruit_type);
CREATE INDEX IF NOT EXISTS idx_varieties_fruit ON public.fruit_varieties(fruit_type);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON public.ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON public.ai_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_calendar_fruit ON public.farming_calendar(fruit_type);
CREATE INDEX IF NOT EXISTS idx_calendar_month ON public.farming_calendar(month);

-- ============================================================================
-- TRIGGERS FOR updated_at
-- ============================================================================
DROP TRIGGER IF EXISTS trg_update_diseases_updated_at ON public.diseases;
CREATE TRIGGER trg_update_diseases_updated_at
BEFORE UPDATE ON public.diseases
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_update_treatments_updated_at ON public.treatments;
CREATE TRIGGER trg_update_treatments_updated_at
BEFORE UPDATE ON public.treatments
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_update_export_requirements_updated_at ON public.export_requirements;
CREATE TRIGGER trg_update_export_requirements_updated_at
BEFORE UPDATE ON public.export_requirements
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_update_ai_conversations_updated_at ON public.ai_conversations;
CREATE TRIGGER trg_update_ai_conversations_updated_at
BEFORE UPDATE ON public.ai_conversations
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================
ALTER TABLE public.diseases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.treatments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mrl_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.export_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fruit_varieties ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.farming_calendar ENABLE ROW LEVEL SECURITY;

-- Read-only access for authenticated users on knowledge base tables
CREATE POLICY "Knowledge base readable by authenticated users" ON public.diseases
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Knowledge base readable by authenticated users" ON public.treatments
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Knowledge base readable by authenticated users" ON public.mrl_limits
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Knowledge base readable by authenticated users" ON public.export_requirements
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Knowledge base readable by authenticated users" ON public.fruit_varieties
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Knowledge base readable by authenticated users" ON public.farming_calendar
  FOR SELECT TO authenticated USING (true);

-- Users can only access their own conversations
CREATE POLICY "Users can view own conversations" ON public.ai_conversations
  FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Users can create own conversations" ON public.ai_conversations
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversations" ON public.ai_conversations
  FOR UPDATE TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own conversations" ON public.ai_conversations
  FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- Admin full access policies
CREATE POLICY "Admins can manage diseases" ON public.diseases
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

CREATE POLICY "Admins can manage treatments" ON public.treatments
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

CREATE POLICY "Admins can manage mrl_limits" ON public.mrl_limits
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

CREATE POLICY "Admins can manage export_requirements" ON public.export_requirements
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

CREATE POLICY "Admins can manage fruit_varieties" ON public.fruit_varieties
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

CREATE POLICY "Admins can manage farming_calendar" ON public.farming_calendar
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE public.diseases IS 'Disease knowledge base for AI assistant';
COMMENT ON TABLE public.treatments IS 'Treatment options linked to diseases';
COMMENT ON TABLE public.mrl_limits IS 'Maximum Residue Limits for export compliance';
COMMENT ON TABLE public.export_requirements IS 'Country-specific export requirements';
COMMENT ON TABLE public.fruit_varieties IS 'Pakistani fruit varieties information';
COMMENT ON TABLE public.ai_conversations IS 'AI assistant conversation history';
COMMENT ON TABLE public.farming_calendar IS 'Monthly farming activities calendar';
