-- Migration: Add Google OAuth support to users table
-- Date: 2025-09-26
-- Description: Adds Google OAuth fields to support Google login/signup

-- Add Google OAuth fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE,
ADD COLUMN IF NOT EXISTS profile_picture VARCHAR(500),
ADD COLUMN IF NOT EXISTS is_google_user BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS provider VARCHAR(50) DEFAULT 'local';

-- Create index on google_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

-- Create index on provider for filtering
CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider);

-- Update existing users to have provider = 'local' if null
UPDATE users 
SET provider = 'local' 
WHERE provider IS NULL;

-- Make password_hash nullable for Google OAuth users (if not already)
-- Note: This might need to be adjusted based on your current schema
-- ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- Add constraint to ensure Google users have google_id
-- ALTER TABLE users ADD CONSTRAINT check_google_user_has_id 
-- CHECK (
--     (is_google_user = FALSE AND google_id IS NULL) OR 
--     (is_google_user = TRUE AND google_id IS NOT NULL)
-- );

-- Add constraint to ensure local users have password
-- ALTER TABLE users ADD CONSTRAINT check_local_user_has_password 
-- CHECK (
--     (provider = 'google' AND password_hash IS NULL) OR 
--     (provider = 'local' AND password_hash IS NOT NULL)
-- );

COMMENT ON COLUMN users.google_id IS 'Google OAuth user identifier';
COMMENT ON COLUMN users.profile_picture IS 'URL to user profile picture from Google';
COMMENT ON COLUMN users.is_google_user IS 'Flag indicating if user registered via Google OAuth';
COMMENT ON COLUMN users.provider IS 'Authentication provider: local or google';