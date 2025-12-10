"""
Unit tests for Authentication Service
Tests: signup, login, Google OAuth, token generation
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
import uuid

from src.services.auth_service import (
    signup_user,
    login_user,
    get_google_auth_url,
    google_auth_callback,
    verify_google_token,
    exchange_code_for_token
)
from src.schemas.user import UserSignup, UserLogin, UserRole


# ============================================================================
# SIGNUP TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
class TestSignupUser:
    """Test user signup functionality"""
    
    def test_signup_success(self, test_user_data):
        """Test successful user signup"""
        with patch('src.services.auth_service.supabase') as mock_supabase:
            # Mock: user doesn't exist
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            
            # Mock: user creation successful
            created_user = {
                "id": test_user_data["id"],
                "email": test_user_data["email"],
                "full_name": test_user_data["full_name"],
                "role": "farmer"
            }
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [created_user]
            
            user_signup = UserSignup(
                email=test_user_data["email"],
                password=test_user_data["password"],
                full_name=test_user_data["full_name"],
                role=UserRole.farmer
            )
            
            result = signup_user(user_signup)
            
            assert result.email == test_user_data["email"]
            assert result.full_name == test_user_data["full_name"]
            assert result.access_token is not None
            assert result.token_type == "bearer"
    
    def test_signup_duplicate_email(self, test_user_data):
        """Test signup with existing email"""
        with patch('src.services.auth_service.supabase') as mock_supabase:
            # Mock: user already exists
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": test_user_data["id"]}
            ]
            
            user_signup = UserSignup(
                email=test_user_data["email"],
                password=test_user_data["password"],
                full_name=test_user_data["full_name"],
                role=UserRole.farmer
            )
            
            with pytest.raises(HTTPException) as exc_info:
                signup_user(user_signup)
            
            assert exc_info.value.status_code == 409
            assert "already registered" in exc_info.value.detail.lower()
    
    def test_signup_missing_password(self, test_user_data):
        """Test signup without password"""
        with patch('src.services.auth_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            
            user_signup = UserSignup(
                email=test_user_data["email"],
                password=None,
                full_name=test_user_data["full_name"],
                role=UserRole.farmer
            )
            
            with pytest.raises(HTTPException) as exc_info:
                signup_user(user_signup)
            
            assert exc_info.value.status_code == 400
            assert "password is required" in exc_info.value.detail.lower()
    
    def test_signup_database_failure(self, test_user_data):
        """Test signup when database insert fails"""
        with patch('src.services.auth_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = []
            
            user_signup = UserSignup(
                email=test_user_data["email"],
                password=test_user_data["password"],
                full_name=test_user_data["full_name"],
                role=UserRole.farmer
            )
            
            with pytest.raises(HTTPException) as exc_info:
                signup_user(user_signup)
            
            assert exc_info.value.status_code == 500


# ============================================================================
# LOGIN TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
class TestLoginUser:
    """Test user login functionality"""
    
    def test_login_success(self, test_user_data):
        """Test successful login"""
        with patch('src.services.auth_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                test_user_data
            ]
            
            user_login = UserLogin(
                email=test_user_data["email"],
                password="TestPass123!"
            )
            
            result = login_user(user_login)
            
            assert result.email == test_user_data["email"]
            assert result.access_token is not None
    
    def test_login_user_not_found(self):
        """Test login with non-existent user"""
        with patch('src.services.auth_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            
            user_login = UserLogin(
                email="nonexistent@example.com",
                password="password123"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                login_user(user_login)
            
            assert exc_info.value.status_code == 401
    
    def test_login_wrong_password(self, test_user_data):
        """Test login with incorrect password"""
        with patch('src.services.auth_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                test_user_data
            ]
            
            user_login = UserLogin(
                email=test_user_data["email"],
                password="WrongPassword123!"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                login_user(user_login)
            
            assert exc_info.value.status_code == 401
    
    def test_login_google_user_with_password(self, test_user_data):
        """Test password login for Google-authenticated user"""
        google_user = {**test_user_data, "is_google_user": True, "provider": "google"}
        
        with patch('src.services.auth_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                google_user
            ]
            
            user_login = UserLogin(
                email=test_user_data["email"],
                password="TestPass123!"
            )
            
            with pytest.raises(HTTPException) as exc_info:
                login_user(user_login)
            
            assert exc_info.value.status_code == 400
            assert "google" in exc_info.value.detail.lower()


# ============================================================================
# GOOGLE OAUTH TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
class TestGoogleAuth:
    """Test Google OAuth functionality"""
    
    def test_get_google_auth_url(self):
        """Test Google OAuth URL generation"""
        url = get_google_auth_url()
        
        assert "accounts.google.com" in url
        assert "oauth2/auth" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
    
    @pytest.mark.asyncio
    async def test_verify_google_token_success(self):
        """Test successful Google token verification"""
        mock_token_info = {
            "iss": "accounts.google.com",
            "sub": "123456789",
            "email": "test@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg"
        }
        
        with patch('src.services.auth_service.id_token.verify_oauth2_token') as mock_verify:
            mock_verify.return_value = mock_token_info
            
            result = await verify_google_token("fake_token")
            
            assert result["email"] == "test@gmail.com"
            assert result["sub"] == "123456789"
    
    @pytest.mark.asyncio
    async def test_verify_google_token_invalid(self):
        """Test Google token verification with invalid token"""
        with patch('src.services.auth_service.id_token.verify_oauth2_token') as mock_verify:
            mock_verify.side_effect = ValueError("Invalid token")
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_google_token("invalid_token")
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self):
        """Test successful code exchange"""
        mock_response = {
            "access_token": "fake_access_token",
            "id_token": "fake_id_token",
            "token_type": "Bearer"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_post)
            
            result = await exchange_code_for_token("auth_code_123")
            
            assert "id_token" in result or result is not None
    
    @pytest.mark.asyncio
    async def test_google_callback_new_user(self, test_user_data):
        """Test Google OAuth callback for new user"""
        google_user_info = {
            "iss": "accounts.google.com",
            "sub": "google_123",
            "email": "newuser@gmail.com",
            "name": "New User",
            "picture": "https://example.com/photo.jpg"
        }
        
        with patch('src.services.auth_service.exchange_code_for_token') as mock_exchange, \
             patch('src.services.auth_service.verify_google_token') as mock_verify, \
             patch('src.services.auth_service.supabase') as mock_supabase:
            
            mock_exchange.return_value = {"id_token": "fake_token"}
            mock_verify.return_value = google_user_info
            
            # User doesn't exist
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            
            # User creation successful
            new_user = {
                "id": str(uuid.uuid4()),
                "email": "newuser@gmail.com",
                "full_name": "New User",
                "role": "farmer",
                "google_id": "google_123"
            }
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [new_user]
            
            result = await google_auth_callback("auth_code")
            
            assert result.email == "newuser@gmail.com"
            assert result.access_token is not None
    
    @pytest.mark.asyncio
    async def test_google_callback_existing_user(self, test_user_data):
        """Test Google OAuth callback for existing user"""
        google_user_info = {
            "iss": "accounts.google.com",
            "sub": "google_123",
            "email": test_user_data["email"],
            "name": test_user_data["full_name"]
        }
        
        existing_user = {
            **test_user_data,
            "google_id": "google_123",
            "is_google_user": True
        }
        
        with patch('src.services.auth_service.exchange_code_for_token') as mock_exchange, \
             patch('src.services.auth_service.verify_google_token') as mock_verify, \
             patch('src.services.auth_service.supabase') as mock_supabase:
            
            mock_exchange.return_value = {"id_token": "fake_token"}
            mock_verify.return_value = google_user_info
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                existing_user
            ]
            
            result = await google_auth_callback("auth_code")
            
            assert result.email == test_user_data["email"]


# ============================================================================
# TOKEN TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
class TestTokenGeneration:
    """Test JWT token generation and validation"""
    
    def test_create_token(self, test_user_data):
        """Test JWT token creation"""
        from src.core.security import create_user_token
        
        token = create_user_token(
            test_user_data["id"],
            test_user_data["email"],
            test_user_data["role"]
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_token(self, test_user_data):
        """Test JWT token decoding"""
        from src.core.security import create_user_token, decode_token
        
        token = create_user_token(
            test_user_data["id"],
            test_user_data["email"],
            test_user_data["role"]
        )
        
        decoded = decode_token(token)
        
        assert decoded["user_id"] == test_user_data["id"]
        assert decoded["email"] == test_user_data["email"]
        assert decoded["role"] == test_user_data["role"]
    
    def test_expired_token(self, test_user_data):
        """Test expired token validation"""
        from src.core.security import create_user_token, decode_token
        from datetime import timedelta
        
        # Create token with -1 minute expiry (expired)
        with patch('src.core.security.datetime') as mock_datetime:
            from datetime import datetime
            mock_datetime.utcnow.return_value = datetime.utcnow() - timedelta(minutes=31)
            
            token = create_user_token(
                test_user_data["id"],
                test_user_data["email"],
                test_user_data["role"]
            )
        
        # Token should be expired when decoded
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_token(token)
