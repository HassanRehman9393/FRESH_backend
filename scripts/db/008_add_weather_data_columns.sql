-- ============================================================================
-- Migration: 008 - Add additional weather data columns
-- Description: Add feels_like, temp_min, temp_max, pressure, visibility, and description fields
-- Author: System
-- Date: 2024
-- ============================================================================

-- Add new columns to weather_data table
ALTER TABLE public.weather_data 
ADD COLUMN IF NOT EXISTS feels_like DECIMAL(5, 2),
ADD COLUMN IF NOT EXISTS temp_min DECIMAL(5, 2),
ADD COLUMN IF NOT EXISTS temp_max DECIMAL(5, 2),
ADD COLUMN IF NOT EXISTS pressure DECIMAL(6, 2),
ADD COLUMN IF NOT EXISTS visibility DECIMAL(10, 2),
ADD COLUMN IF NOT EXISTS description VARCHAR(255);

-- Add constraints for the new columns
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'valid_feels_like') THEN
        ALTER TABLE public.weather_data ADD CONSTRAINT valid_feels_like CHECK (feels_like IS NULL OR feels_like BETWEEN -50 AND 60);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'valid_temp_min') THEN
        ALTER TABLE public.weather_data ADD CONSTRAINT valid_temp_min CHECK (temp_min IS NULL OR temp_min BETWEEN -50 AND 60);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'valid_temp_max') THEN
        ALTER TABLE public.weather_data ADD CONSTRAINT valid_temp_max CHECK (temp_max IS NULL OR temp_max BETWEEN -50 AND 60);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'valid_pressure') THEN
        ALTER TABLE public.weather_data ADD CONSTRAINT valid_pressure CHECK (pressure IS NULL OR pressure >= 0);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'valid_visibility') THEN
        ALTER TABLE public.weather_data ADD CONSTRAINT valid_visibility CHECK (visibility IS NULL OR visibility >= 0);
    END IF;
END $$;

-- Add comments
COMMENT ON COLUMN public.weather_data.feels_like IS 'Perceived temperature accounting for humidity and wind';
COMMENT ON COLUMN public.weather_data.temp_min IS 'Minimum temperature in the area';
COMMENT ON COLUMN public.weather_data.temp_max IS 'Maximum temperature in the area';
COMMENT ON COLUMN public.weather_data.pressure IS 'Atmospheric pressure in hPa';
COMMENT ON COLUMN public.weather_data.visibility IS 'Visibility distance in meters';
COMMENT ON COLUMN public.weather_data.description IS 'Human-readable weather description';
