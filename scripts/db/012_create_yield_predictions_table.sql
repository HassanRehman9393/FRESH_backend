-- 012_create_yield_predictions_table.sql
-- Migration: Create yield_predictions table for Yield Prediction Module
-- Stores fruit orchard yield predictions with ML model results, confidence scores, and comparisons to regional baselines

CREATE TABLE IF NOT EXISTS public.yield_predictions (
  -- Primary key and identification
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  orchard_id UUID,  -- Optional reference to a specific orchard
  
  -- Prediction metadata
  prediction_date TIMESTAMPTZ NOT NULL DEFAULT now(),
  prediction_season INT,  -- Year (e.g., 2026)
  
  -- Fruit and location info
  fruit_type TEXT NOT NULL CHECK (fruit_type IN ('mango', 'orange', 'guava', 'grapefruit')),
  region TEXT NOT NULL DEFAULT 'pakistan',  -- Pakistan-only for current system
  orchard_area_hectares DECIMAL(10, 2) NOT NULL,
  
  -- Core prediction results
  predicted_yield_kg DECIMAL(12, 2) NOT NULL,
  confidence_score DECIMAL(4, 3) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
  confidence_lower_bound_kg DECIMAL(12, 2),  -- 95% CI lower
  confidence_upper_bound_kg DECIMAL(12, 2),  -- 95% CI upper
  
  -- Contributing factors
  health_score DECIMAL(4, 3),  -- 0-1 scale
  ripeness_percentage DECIMAL(5, 2),  -- 0-100
  disease_percentage DECIMAL(5, 2),  -- 0-100
  weather_favorability DECIMAL(4, 3),  -- 0-1 scale
  coverage_score DECIMAL(4, 3),  -- 0-1 scale (% of orchard sampled)
  
  -- Sampling details
  total_fruits_detected INT,
  extrapolated_fruit_count INT,
  sampling_factor DECIMAL(5, 3),  -- Multiplier from sample to full area
  sampling_pattern TEXT CHECK (sampling_pattern IN ('w-shaped', 'zigzag')),
  sampling_confidence DECIMAL(4, 3),
  detection_count INT,
  
  -- Baseline comparison
  regional_baseline_yield_kg DECIMAL(12, 2),
  regional_baseline_std_dev DECIMAL(12, 2),
  variance_from_baseline_percent DECIMAL(6, 2),  -- How much above/below regional average
  
  -- Trend analysis
  trend_direction TEXT CHECK (trend_direction IN ('improving', 'stable', 'declining', 'unknown')),
  
  -- ML model metadata
  model_used TEXT CHECK (model_used IN ('xgboost', 'linear_regression', 'baseline')),
  model_version TEXT,
  
  -- Historical user yield data
  user_historical_average_yield_kg DECIMAL(12, 2),
  user_historical_trend TEXT CHECK (user_historical_trend IN ('improving', 'stable', 'declining', 'insufficient_data')),
  
  -- Input aggregation window
  aggregation_period_days INT DEFAULT 30,
  
  -- Flags
  prediction_used_fallback BOOLEAN DEFAULT FALSE,  -- True if fell back to baseline
  notes TEXT,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes for common queries
CREATE INDEX idx_yield_predictions_user_id ON public.yield_predictions(user_id);
CREATE INDEX idx_yield_predictions_fruit_type ON public.yield_predictions(fruit_type);
CREATE INDEX idx_yield_predictions_prediction_date ON public.yield_predictions(prediction_date DESC);
CREATE INDEX idx_yield_predictions_user_fruit_date ON public.yield_predictions(user_id, fruit_type, prediction_date DESC);
CREATE INDEX idx_yield_predictions_season ON public.yield_predictions(prediction_season);

-- Trigger to auto-update "updated_at" on row updates
DROP TRIGGER IF EXISTS trg_update_yield_predictions_updated_at ON public.yield_predictions;
CREATE TRIGGER trg_update_yield_predictions_updated_at
BEFORE UPDATE ON public.yield_predictions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- Historical yield tracking table (for user's actual harvests)
CREATE TABLE IF NOT EXISTS public.user_harvest_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  
  -- Harvest details
  fruit_type TEXT NOT NULL CHECK (fruit_type IN ('mango', 'orange', 'guava', 'grapefruit')),
  orchard_area_hectares DECIMAL(10, 2) NOT NULL,
  actual_yield_kg DECIMAL(12, 2) NOT NULL,
  yield_per_hectare DECIMAL(12, 2) NOT NULL,
  
  -- Context
  harvest_date DATE NOT NULL,
  season INT NOT NULL,  -- Year of harvest
  
  -- Weather/conditions during harvest
  weather_conditions JSONB,  -- {temperature_avg, rainfall, humidity, notes}
  quality_notes TEXT,
  
  -- Link to prediction (if exists)
  related_prediction_id UUID REFERENCES public.yield_predictions(id) ON DELETE SET NULL,
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes
CREATE INDEX idx_harvest_records_user_id ON public.user_harvest_records(user_id);
CREATE INDEX idx_harvest_records_fruit_type ON public.user_harvest_records(fruit_type);
CREATE INDEX idx_harvest_records_harvest_date ON public.user_harvest_records(harvest_date DESC);
CREATE INDEX idx_harvest_records_season ON public.user_harvest_records(season);

-- Trigger for user_harvest_records
DROP TRIGGER IF EXISTS trg_update_harvest_records_updated_at ON public.user_harvest_records;
CREATE TRIGGER trg_update_harvest_records_updated_at
BEFORE UPDATE ON public.user_harvest_records
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- Grant permissions (adjust based on your Supabase roles)
GRANT SELECT, INSERT, UPDATE, DELETE ON public.yield_predictions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_harvest_records TO authenticated;
