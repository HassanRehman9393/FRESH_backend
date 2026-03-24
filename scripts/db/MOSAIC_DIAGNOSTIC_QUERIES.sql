-- GPS Mosaic Map - SQL Queries for Diagnostics and Management
-- This file contains useful SQL queries for monitoring and managing the ortho-mosaic system

-- ============================================================================
-- 1. DIAGNOSTIC QUERIES
-- ============================================================================

-- Check total images with GPS coverage
SELECT 
  COUNT(*) as total_images,
  COUNT(CASE WHEN metadata->>'gps_latitude' IS NOT NULL THEN 1 END) as images_with_gps,
  ROUND(COUNT(CASE WHEN metadata->>'gps_latitude' IS NOT NULL THEN 1 END) * 100.0 / 
        NULLIF(COUNT(*), 0), 1) as gps_coverage_percent
FROM images;

-- GPS coverage by user
SELECT 
  user_id,
  COUNT(*) as total_images,
  COUNT(CASE WHEN metadata->>'gps_latitude' IS NOT NULL THEN 1 END) as images_with_gps,
  ROUND(COUNT(CASE WHEN metadata->>'gps_latitude' IS NOT NULL THEN 1 END) * 100.0 / 
        NULLIF(COUNT(*), 0), 1) as coverage_percent
FROM images
GROUP BY user_id
ORDER BY images_with_gps DESC;

-- Find images with complete GPS data
SELECT 
  id,
  file_name,
  metadata->>'gps_latitude' as latitude,
  metadata->>'gps_longitude' as longitude,
  metadata->>'gps_altitude' as altitude,
  created_at
FROM images
WHERE metadata->>'gps_latitude' IS NOT NULL 
  AND metadata->>'gps_longitude' IS NOT NULL
ORDER BY created_at DESC;

-- Find images missing GPS data
SELECT 
  id,
  file_name,
  metadata,
  created_at
FROM images
WHERE metadata->>'gps_latitude' IS NULL 
  OR metadata->>'gps_longitude' IS NULL
ORDER BY created_at DESC;

-- ============================================================================
-- 2. BOUNDS CALCULATION QUERIES
-- ============================================================================

-- Calculate mosaic bounds for a specific user
SELECT 
  user_id,
  MIN(CAST(metadata->>'gps_latitude' AS FLOAT)) as min_lat,
  MAX(CAST(metadata->>'gps_latitude' AS FLOAT)) as max_lat,
  MIN(CAST(metadata->>'gps_longitude' AS FLOAT)) as min_lon,
  MAX(CAST(metadata->>'gps_longitude' AS FLOAT)) as max_lon,
  (MIN(CAST(metadata->>'gps_latitude' AS FLOAT)) + 
   MAX(CAST(metadata->>'gps_latitude' AS FLOAT))) / 2 as center_lat,
  (MIN(CAST(metadata->>'gps_longitude' AS FLOAT)) + 
   MAX(CAST(metadata->>'gps_longitude' AS FLOAT))) / 2 as center_lon,
  COUNT(*) as image_count
FROM images
WHERE metadata->>'gps_latitude' IS NOT NULL 
  AND metadata->>'gps_longitude' IS NOT NULL
GROUP BY user_id;

-- Calculate coverage area in square kilometers
SELECT 
  user_id,
  MIN(CAST(metadata->>'gps_latitude' AS FLOAT)) as min_lat,
  MAX(CAST(metadata->>'gps_latitude' AS FLOAT)) as max_lat,
  MIN(CAST(metadata->>'gps_longitude' AS FLOAT)) as min_lon,
  MAX(CAST(metadata->>'gps_longitude' AS FLOAT)) as max_lon,
  ROUND(
    ((MAX(CAST(metadata->>'gps_longitude' AS FLOAT)) - 
      MIN(CAST(metadata->>'gps_longitude' AS FLOAT))) * 111.0 *
     (MAX(CAST(metadata->>'gps_latitude' AS FLOAT)) - 
      MIN(CAST(metadata->>'gps_latitude' AS FLOAT))) * 111.0)::numeric, 2
  ) as approximate_area_km2,
  COUNT(*) as image_count
FROM images
WHERE metadata->>'gps_latitude' IS NOT NULL 
  AND metadata->>'gps_longitude' IS NOT NULL
GROUP BY user_id;

-- ============================================================================
-- 3. ALTITUDE ANALYSIS QUERIES
-- ============================================================================

-- Altitude statistics
SELECT 
  user_id,
  COUNT(*) as total_with_gps,
  COUNT(CASE WHEN metadata->>'gps_altitude' IS NOT NULL THEN 1 END) as with_altitude,
  ROUND(CAST(MIN(metadata->>'gps_altitude') AS FLOAT)::numeric, 2) as min_altitude_m,
  ROUND(CAST(MAX(metadata->>'gps_altitude') AS FLOAT)::numeric, 2) as max_altitude_m,
  ROUND(CAST(AVG(CAST(metadata->>'gps_altitude' AS FLOAT)) AS FLOAT)::numeric, 2) as avg_altitude_m
FROM images
WHERE metadata->>'gps_latitude' IS NOT NULL 
  AND metadata->>'gps_longitude' IS NOT NULL
GROUP BY user_id;

-- Detect altitude anomalies
SELECT 
  id,
  file_name,
  metadata->>'gps_latitude' as latitude,
  metadata->>'gps_longitude' as longitude,
  metadata->>'gps_altitude' as altitude,
  created_at
FROM images
WHERE metadata->>'gps_altitude' IS NOT NULL
  AND (
    CAST(metadata->>'gps_altitude' AS FLOAT) > 10000  -- Unrealistic altitude (>10km)
    OR CAST(metadata->>'gps_altitude' AS FLOAT) < -500  -- Unrealistic negative altitude
  );

-- ============================================================================
-- 4. TIME-SERIES & TEMPORAL QUERIES
-- ============================================================================

-- Images uploaded by day
SELECT 
  DATE(created_at) as upload_date,
  COUNT(*) as total_uploaded,
  COUNT(CASE WHEN metadata->>'gps_latitude' IS NOT NULL THEN 1 END) as with_gps
FROM images
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY upload_date DESC;

-- Images uploaded by hour (last 7 days)
SELECT 
  DATE_TRUNC('hour', created_at) as hour,
  COUNT(*) as images_uploaded
FROM images
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;

-- ============================================================================
-- 5. GPS COORDINATE VALIDATION QUERIES
-- ============================================================================

-- Find invalid GPS coordinates
SELECT 
  id,
  file_name,
  metadata->>'gps_latitude' as latitude,
  metadata->>'gps_longitude' as longitude,
  created_at,
  CASE 
    WHEN CAST(metadata->>'gps_latitude' AS FLOAT) < -90 
      OR CAST(metadata->>'gps_latitude' AS FLOAT) > 90 THEN 'Invalid Latitude'
    WHEN CAST(metadata->>'gps_longitude' AS FLOAT) < -180 
      OR CAST(metadata->>'gps_longitude' AS FLOAT) > 180 THEN 'Invalid Longitude'
    ELSE 'Unknown Error'
  END as error_type
FROM images
WHERE metadata->>'gps_latitude' IS NOT NULL 
  AND metadata->>'gps_longitude' IS NOT NULL
  AND (
    CAST(metadata->>'gps_latitude' AS FLOAT) < -90 
    OR CAST(metadata->>'gps_latitude' AS FLOAT) > 90
    OR CAST(metadata->>'gps_longitude' AS FLOAT) < -180 
    OR CAST(metadata->>'gps_longitude' AS FLOAT) > 180
  );

-- ============================================================================
-- 6. MANAGEMENT & CLEANUP QUERIES
-- ============================================================================

-- Count images by file type
SELECT 
  metadata->>'content_type' as file_type,
  COUNT(*) as count,
  ROUND(SUM(CAST(file_path AS TEXT)::int) / 1024.0 / 1024.0, 2) as total_size_mb
FROM images
GROUP BY metadata->>'content_type'
ORDER BY count DESC;

-- Find duplicate or suspicious files
SELECT 
  file_name,
  COUNT(*) as occurrences,
  ARRAY_AGG(id) as image_ids,
  ARRAY_AGG(user_id) as user_ids
FROM images
GROUP BY file_name
HAVING COUNT(*) > 1
ORDER BY occurrences DESC;

-- Storage usage by user
SELECT 
  user_id,
  COUNT(*) as image_count,
  ROUND(SUM(CAST(metadata->>'file_size' AS FLOAT)) / 1024.0 / 1024.0, 2) as total_storage_mb
FROM images
GROUP BY user_id
ORDER BY total_storage_mb DESC;

-- ============================================================================
-- 7. PERFORMANCE MONITORING QUERIES
-- ============================================================================

-- Images created per minute (spike detection)
SELECT 
  DATE_TRUNC('minute', created_at) as minute,
  COUNT(*) as images_uploaded
FROM images
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY DATE_TRUNC('minute', created_at)
ORDER BY minute DESC;

-- Database table size
SELECT 
  pg_size_pretty(pg_total_relation_size('public.images')) as total_size,
  pg_size_pretty(pg_relation_size('public.images')) as table_size,
  pg_size_pretty(pg_indexes_size('public.images')) as indexes_size,
  COUNT(*) as total_records
FROM images;

-- ============================================================================
-- 8. MOSAIC-SPECIFIC QUERIES
-- ============================================================================

-- Get GPS bounds for mosaic rendering
-- Replace {user_id} with actual user UUID
SELECT 
  MIN(CAST(metadata->>'gps_latitude' AS FLOAT)) as min_lat,
  MAX(CAST(metadata->>'gps_latitude' AS FLOAT)) as max_lat,
  MIN(CAST(metadata->>'gps_longitude' AS FLOAT)) as min_lon,
  MAX(CAST(metadata->>'gps_longitude' AS FLOAT)) as max_lon,
  (MIN(CAST(metadata->>'gps_latitude' AS FLOAT)) + 
   MAX(CAST(metadata->>'gps_latitude' AS FLOAT))) / 2 as center_lat,
  (MIN(CAST(metadata->>'gps_longitude' AS FLOAT)) + 
   MAX(CAST(metadata->>'gps_longitude' AS FLOAT))) / 2 as center_lon,
  COUNT(*) as total_images
FROM images
WHERE user_id = '{user_id}'
  AND metadata->>'gps_latitude' IS NOT NULL 
  AND metadata->>'gps_longitude' IS NOT NULL;

-- Get all image details for GeoJSON generation
-- Replace {user_id} with actual user UUID
SELECT 
  id,
  file_name,
  file_path as image_url,
  CAST(metadata->>'gps_latitude' AS FLOAT) as latitude,
  CAST(metadata->>'gps_longitude' AS FLOAT) as longitude,
  CAST(metadata->>'gps_altitude' AS FLOAT) as altitude,
  created_at as timestamp,
  file_name || ' - GPS (' || 
    ROUND(CAST(metadata->>'gps_latitude' AS FLOAT)::numeric, 6) || ', ' ||
    ROUND(CAST(metadata->>'gps_longitude' AS FLOAT)::numeric, 6) || ')' as description
FROM images
WHERE user_id = '{user_id}'
  AND metadata->>'gps_latitude' IS NOT NULL 
  AND metadata->>'gps_longitude' IS NOT NULL
ORDER BY created_at DESC;

-- Find images within a geographic bounding box
-- Useful for filtering by survey area
-- Replace bounds with actual coordinates
SELECT 
  id,
  file_name,
  CAST(metadata->>'gps_latitude' AS FLOAT) as latitude,
  CAST(metadata->>'gps_longitude' AS FLOAT) as longitude,
  created_at
FROM images
WHERE CAST(metadata->>'gps_latitude' AS FLOAT) BETWEEN 33.67 AND 33.68
  AND CAST(metadata->>'gps_longitude' AS FLOAT) BETWEEN 73.13 AND 73.14
ORDER BY created_at DESC;

-- ============================================================================
-- 9. MAINTENANCE QUERIES
-- ============================================================================

-- Update GPS data format (if needed)
-- Example: Convert from DMS to decimal degrees if stored as string
UPDATE images
SET metadata = jsonb_set(
  metadata,
  '{gps_latitude_original}',
  to_jsonb(metadata->>'gps_latitude')
)
WHERE metadata->>'gps_latitude' IS NOT NULL
  AND metadata->>'gps_latitude_original' IS NULL;

-- Remove duplicate old GPS entries (if migrating data)
DELETE FROM images
WHERE id NOT IN (
  SELECT DISTINCT ON (file_name, user_id) id
  FROM images
  WHERE metadata->>'gps_latitude' IS NOT NULL
  ORDER BY file_name, user_id, created_at DESC
)
AND metadata->>'gps_latitude' IS NOT NULL;

-- ============================================================================
-- 10. ANALYTICS QUERIES
-- ============================================================================

-- Most active users (by image uploads)
SELECT 
  user_id,
  COUNT(*) as total_images,
  COUNT(CASE WHEN metadata->>'gps_latitude' IS NOT NULL THEN 1 END) as gps_images,
  MAX(created_at) as last_upload
FROM images
GROUP BY user_id
ORDER BY total_images DESC
LIMIT 10;

-- Average images per survey session
SELECT 
  user_id,
  DATE(created_at) as session_date,
  COUNT(*) as images_per_session
FROM images
WHERE metadata->>'gps_latitude' IS NOT NULL
GROUP BY user_id, DATE(created_at)
ORDER BY user_id, DATE(created_at) DESC;

-- Popular survey times (hour of day analysis)
SELECT 
  EXTRACT(HOUR FROM created_at) as hour_of_day,
  COUNT(*) as total_uploads,
  COUNT(CASE WHEN metadata->>'gps_latitude' IS NOT NULL THEN 1 END) as with_gps
FROM images
GROUP BY EXTRACT(HOUR FROM created_at)
ORDER BY hour_of_day;

-- ============================================================================
-- NOTES
-- ============================================================================
-- These queries assume:
-- 1. Table name: public.images
-- 2. GPS data stored in: metadata JSON field as gps_latitude, gps_longitude, gps_altitude
-- 3. PostgreSQL 12+ (for JSON functions)
-- 4. User IDs are UUIDs
-- 
-- Performance Tips:
-- - Add index on metadata->>'gps_latitude' for fast filtering
-- - Add index on (user_id, created_at) for timeline queries
-- - Consider partitioning by user_id for very large tables
-- 
-- Example indexes to create:
-- CREATE INDEX idx_images_gps_latitude ON images((metadata->>'gps_latitude'));
-- CREATE INDEX idx_images_gps_longitude ON images((metadata->>'gps_longitude'));
-- CREATE INDEX idx_images_user_created ON images(user_id, created_at);
-- CREATE INDEX idx_images_user_gps_composite ON images(user_id)
--   WHERE metadata->>'gps_latitude' IS NOT NULL;
