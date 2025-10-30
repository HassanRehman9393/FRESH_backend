# FRESH Backend API - Deployment Guide

## 🚀 Quick Fixes for Production Issues

### Issue 1: bcrypt Version Compatibility Error

**Error Message:**
```
(trapped) error reading bcrypt version
AttributeError: module 'bcrypt' has no attribute '__about__'
```

**Root Cause:**
- Newer versions of bcrypt (4.0+) removed the `__about__` module
- `passlib` tries to access `bcrypt.__about__.__version__` for version detection
- This causes authentication to fail in production

**Solution Applied:**
The codebase has been updated to use `bcrypt` directly instead of going through `passlib`:

1. **Updated `requirements.txt`:**
   - Removed dependency on `passlib[bcrypt]`
   - Added direct bcrypt dependency: `bcrypt>=4.0.1,<5.0.0`

2. **Updated `src/core/security.py`:**
   - Now uses `bcrypt` directly for hashing and verification
   - Bypasses passlib's version detection mechanism
   - Handles password length limits (72 bytes) automatically

**Deployment Steps:**
```bash
# 1. Pull latest code
git pull origin main

# 2. Update dependencies
pip install --upgrade bcrypt>=4.0.1,<5.0.0

# 3. If using passlib, uninstall it
pip uninstall passlib -y

# 4. Reinstall all requirements
pip install -r requirements.txt

# 5. Restart your application
```

---

### Issue 2: Password Length Error

**Error Message:**
```
Error verifying password: password cannot be longer than 72 bytes
```

**Root Cause:**
- bcrypt has a hard limit of 72 bytes for passwords
- Long passwords or special characters can exceed this limit

**Solution Applied:**
The password handling functions now automatically truncate passwords to 72 bytes:

```python
# In src/core/security.py
def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > MAX_PASSWORD_LENGTH:  # 72 bytes
        password_bytes = password_bytes[:MAX_PASSWORD_LENGTH]
    # ... hash password
```

**No action required** - This is handled automatically in the code.

---

### Issue 3: ML API Timeout

**Error Message:**
```
Error in process_single_image: The read operation timed out
Failed to process image: Failed to communicate with ML API: All connection attempts failed
```

**Root Cause:**
- ML model inference takes longer than the default HTTP timeout
- Network issues between backend and ML API
- ML API not responding or unreachable

**Solution Applied:**

1. **Extended Timeout Configuration:**
   ```python
   # In src/core/config.py
   ml_api_timeout: int = 300  # 5 minutes default
   ```

2. **Retry Logic with Exponential Backoff:**
   - Retries failed requests up to 3 times
   - Uses exponential backoff: 1s, 2s, 4s between retries
   - Only retries on timeout errors (not on 4xx/5xx errors)

3. **Improved httpx.Timeout Configuration:**
   ```python
   timeout = httpx.Timeout(
       timeout=300,      # Overall timeout
       connect=10.0,     # Connection timeout
       read=300,         # Read timeout (critical for ML processing)
       write=10.0,       # Write timeout
       pool=5.0          # Pool timeout
   )
   ```

**Deployment Configuration:**

Add these environment variables to your production environment:

```env
# ML API Configuration
ML_API_URL=https://your-ml-api-url.com
ML_API_TIMEOUT=300
ML_API_MAX_RETRIES=3
```

**For Railway/DigitalOcean/Heroku:**
```bash
# Set environment variables
railway variables set ML_API_URL=https://your-ml-api-url.com
railway variables set ML_API_TIMEOUT=300
railway variables set ML_API_MAX_RETRIES=3
```

---

## 📋 Complete Environment Variables Checklist

Ensure all these variables are set in your production environment:

### Required Variables
```env
# Database
DATABASE_URL=postgresql://...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Security
SECRET_KEY=your-production-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=False
APP_NAME=FRESH Backend API
APP_VERSION=1.0.0

# ML API
ML_API_URL=https://your-ml-api-url.com
ML_API_TIMEOUT=300
ML_API_MAX_RETRIES=3

# CORS
ALLOWED_ORIGINS=https://your-frontend.com,https://your-other-domain.com

# File Upload
MAX_FILE_SIZE=10485760
ALLOWED_FILE_TYPES=image/jpeg,image/png,image/webp
```

### Optional Variables
```env
# Redis (if using caching)
REDIS_URL=redis://...

# Google OAuth (if using)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-backend.com/api/auth/google/callback
```

---

## 🔄 Deployment Steps

### 1. Update Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
Configure all required environment variables in your hosting platform.

### 3. Database Migrations
```bash
# Run any pending migrations
python scripts/db/run_migrations.py
```

### 4. Test the Deployment
```bash
# Health check
curl https://your-backend.com/health

# Expected response:
{
  "status": "healthy",
  "service": "FRESH Backend API",
  "version": "1.0.0",
  "database": "connected"
}
```

### 5. Monitor Logs
Watch for these success indicators:
- ✅ Database connection successful
- 🔧 CORS configuration loaded
- 🚀 Application started

---

## 🐛 Troubleshooting Production Issues

### Check Logs
```bash
# Railway
railway logs

# Heroku
heroku logs --tail

# DigitalOcean App Platform
doctl apps logs <app-id> --follow
```

### Common Production Errors

1. **Database Connection Failed**
   - Verify DATABASE_URL is correct
   - Check firewall rules allow connections
   - Verify Supabase project is active

2. **CORS Errors**
   - Add your frontend domain to ALLOWED_ORIGINS
   - Don't use wildcards (*) in production
   - Include both http and https if needed

3. **ML API Not Responding**
   - Verify ML_API_URL is accessible
   - Check ML API is deployed and running
   - Increase ML_API_TIMEOUT if processing takes longer
   - Check network connectivity between services

4. **Authentication Failing**
   - Verify SECRET_KEY is set and consistent
   - Check bcrypt version is >=4.0.1
   - Ensure user passwords in database are valid bcrypt hashes

---

## 📊 Performance Optimization

### 1. ML API Timeouts
For large images or batch processing:
```env
ML_API_TIMEOUT=600  # 10 minutes
```

### 2. Connection Pooling
Adjust if you have many concurrent users:
```python
# In database configuration
pool_size=20
max_overflow=10
```

### 3. Caching
Enable Redis caching for frequently accessed data:
```env
REDIS_URL=redis://your-redis-instance:6379
```

---

## 🔒 Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` (at least 32 characters)
- [ ] Database uses SSL/TLS connections
- [ ] CORS configured with specific domains (no wildcards)
- [ ] Environment variables stored securely (not in code)
- [ ] Regular security updates: `pip list --outdated`
- [ ] Rate limiting enabled (if applicable)
- [ ] HTTPS enforced for all endpoints

---

## 📈 Monitoring Recommendations

1. **Set up health check monitoring:**
   - Use UptimeRobot, Pingdom, or similar
   - Monitor `/health` endpoint every 5 minutes

2. **Log aggregation:**
   - Collect logs in a centralized location
   - Set up alerts for ERROR level logs

3. **Performance metrics:**
   - Track API response times
   - Monitor ML API timeout rates
   - Watch database connection pool usage

---

## 🆘 Emergency Rollback

If issues persist after deployment:

```bash
# 1. Rollback to previous version
git revert HEAD
git push origin main

# 2. Or redeploy previous version
railway rollback  # Railway
heroku releases:rollback  # Heroku

# 3. Check if issue is resolved
curl https://your-backend.com/health
```

---

## 📞 Support

If you encounter issues not covered in this guide:

1. Check the logs first
2. Review the troubleshooting section in README.md
3. Verify all environment variables are set correctly
4. Test locally with production environment variables

---

**Last Updated:** October 30, 2024  
**Version:** 1.0.0

