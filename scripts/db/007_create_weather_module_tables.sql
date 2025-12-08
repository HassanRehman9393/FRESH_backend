-- 007_create_weather_module_tables.sql
-- Migration: Create weather integration module tables for FRESH Backend API
-- Purpose: Real-time weather data, alerts, risk analysis, and disease correlation
-- Based on: Weather Module PRD

-- ============================================================================
-- Table 1: orchards
-- Purpose: Store orchard location and user mapping
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.orchards (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  latitude DECIMAL(10, 8) NOT NULL,
  longitude DECIMAL(11, 8) NOT NULL,
  area_hectares DECIMAL(10, 2),
  fruit_types JSONB DEFAULT '[]'::jsonb,  -- ["mango", "guava"]
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  CONSTRAINT valid_latitude CHECK (latitude BETWEEN -90 AND 90),
  CONSTRAINT valid_longitude CHECK (longitude BETWEEN -180 AND 180),
  CONSTRAINT valid_area CHECK (area_hectares IS NULL OR area_hectares > 0)
);

CREATE INDEX IF NOT EXISTS idx_orchards_user_id ON public.orchards(user_id);

DROP TRIGGER IF EXISTS trg_update_orchards_updated_at ON public.orchards;
CREATE TRIGGER trg_update_orchards_updated_at
BEFORE UPDATE ON public.orchards
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- Table 2: weather_data
-- Purpose: Store historical weather records for analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.weather_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  orchard_id UUID NOT NULL REFERENCES public.orchards(id) ON DELETE CASCADE,
  temperature DECIMAL(5, 2) NOT NULL,
  humidity DECIMAL(5, 2) NOT NULL,
  rainfall DECIMAL(6, 2) DEFAULT 0,
  wind_speed DECIMAL(5, 2),
  weather_condition VARCHAR(50),  -- "clear", "rain", "cloudy"
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source VARCHAR(50) NOT NULL DEFAULT 'openweathermap',
  
  CONSTRAINT valid_temperature CHECK (temperature BETWEEN -50 AND 60),
  CONSTRAINT valid_humidity CHECK (humidity BETWEEN 0 AND 100),
  CONSTRAINT valid_rainfall CHECK (rainfall >= 0)
);

CREATE INDEX IF NOT EXISTS idx_weather_data_orchard_id ON public.weather_data(orchard_id);
CREATE INDEX IF NOT EXISTS idx_weather_data_recorded_at ON public.weather_data(recorded_at DESC);

-- ============================================================================
-- Table 3: weather_alerts
-- Purpose: Store alert rules and triggered alerts
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.weather_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  orchard_id UUID NOT NULL REFERENCES public.orchards(id) ON DELETE CASCADE,
  alert_type VARCHAR(100) NOT NULL,  -- "high_humidity", "rainfall", "extreme_temp"
  severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
  message TEXT NOT NULL,
  recommendation TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  acknowledged_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_weather_alerts_orchard_id ON public.weather_alerts(orchard_id);
CREATE INDEX IF NOT EXISTS idx_weather_alerts_active ON public.weather_alerts(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- Table 4: alert_rules
-- Purpose: Configurable thresholds for weather alerts
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.alert_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_name VARCHAR(100) NOT NULL UNIQUE,
  condition_type VARCHAR(50) NOT NULL,  -- "humidity", "temperature", "rainfall"
  threshold_value DECIMAL(10, 2) NOT NULL,
  operator VARCHAR(5) NOT NULL CHECK (operator IN ('>', '<', '>=', '<=')),
  disease_risk VARCHAR(100),  -- "anthracnose", "citrus_canker"
  fruit_types JSONB DEFAULT '[]'::jsonb,
  alert_message_en TEXT NOT NULL,
  alert_message_ur TEXT,
  is_enabled BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON public.alert_rules(is_enabled) WHERE is_enabled = TRUE;

-- ============================================================================
-- Table 5: weather_disease_risk
-- Purpose: Store calculated risk assessments
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.weather_disease_risk (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  orchard_id UUID NOT NULL REFERENCES public.orchards(id) ON DELETE CASCADE,
  disease_type VARCHAR(100) NOT NULL,
  risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('low', 'medium', 'high')),
  contributing_factors JSONB,
  recommendation_en TEXT,
  recommendation_ur TEXT,
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_disease_risk_orchard_id ON public.weather_disease_risk(orchard_id);
CREATE INDEX IF NOT EXISTS idx_disease_risk_calculated_at ON public.weather_disease_risk(calculated_at DESC);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE public.orchards IS 'Store orchard location and user mapping';
COMMENT ON TABLE public.weather_data IS 'Store historical weather records for analysis';
COMMENT ON TABLE public.weather_alerts IS 'Store alert rules and triggered alerts';
COMMENT ON TABLE public.alert_rules IS 'Configurable thresholds for weather alerts';
COMMENT ON TABLE public.weather_disease_risk IS 'Store calculated risk assessments';

-- ============================================================================
-- Migration Complete - 5 tables created as per PRD
-- ============================================================================
