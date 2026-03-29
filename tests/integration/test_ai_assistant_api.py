"""
Integration Tests for AI Assistant API Endpoints
=================================================

Comprehensive API endpoint tests including:
- POST /api/assistant/chat
- GET /api/assistant/conversations
- GET /api/assistant/conversations/{id}
- DELETE /api/assistant/conversations/{id}
- Direct tool endpoints (MRL check, export requirements)

Run with: pytest tests/integration/test_ai_assistant_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
import json


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_ai_agent_service():
    """Mock AIAgentService for API tests."""
    mock = MagicMock()
    mock.process_message = AsyncMock()
    return mock


@pytest.fixture
def mock_supabase_responses():
    """Standard mock responses for Supabase queries."""
    return {
        "conversations": [
            {
                "id": str(uuid4()),
                "user_id": str(uuid4()),
                "title": "Test Conversation",
                "messages": [],
                "created_at": "2026-02-13T10:00:00Z",
                "updated_at": "2026-02-13T10:00:00Z"
            }
        ],
        "diseases": [
            {
                "id": str(uuid4()),
                "name": "anthracnose",
                "name_urdu": "اینتھراکنوز",
                "symptoms": ["Dark spots", "Fruit rot"],
                "causes": "Fungal infection"
            }
        ],
        "mrl_limits": [
            {
                "id": str(uuid4()),
                "pesticide_name": "Carbendazim",
                "fruit_type": "mango",
                "country_code": "EU",
                "mrl_value": 0.1,
                "unit": "mg/kg"
            }
        ]
    }


# ============================================================================
# TEST: CHAT ENDPOINT
# ============================================================================

class TestChatEndpoint:
    """Tests for POST /api/assistant/chat"""
    
    def test_chat_requires_authentication(self, client):
        """Test that chat endpoint requires authentication."""
        response = client.post(
            "/api/assistant/chat",
            json={"message": "Hello"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_chat_success(self, client, auth_headers, mock_ai_agent_service):
        """Test successful chat message."""
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(return_value={
                "response": "Hello! I can help you with fruit diseases.",
                "conversation_id": str(uuid4()),
                "rich_content": None,
                "tools_used": []
            })
            
            response = client.post(
                "/api/assistant/chat",
                json={"message": "Hello"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "conversation_id" in data
    
    def test_chat_with_existing_conversation(self, client, auth_headers):
        """Test chat in existing conversation context."""
        conversation_id = str(uuid4())
        
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(return_value={
                "response": "Continuing our conversation...",
                "conversation_id": conversation_id,
                "rich_content": None,
                "tools_used": []
            })
            
            response = client.post(
                "/api/assistant/chat",
                json={
                    "message": "Tell me more",
                    "conversation_id": conversation_id
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["conversation_id"] == conversation_id
    
    def test_chat_with_disease_query(self, client, auth_headers):
        """Test chat with disease-related query returns rich content."""
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(return_value={
                "response": "Anthracnose is a fungal disease...",
                "conversation_id": str(uuid4()),
                "rich_content": {
                    "type": "disease",
                    "data": {
                        "name": "anthracnose",
                        "symptoms": ["Dark spots", "Fruit rot"]
                    }
                },
                "tools_used": ["get_disease_info"]
            })
            
            response = client.post(
                "/api/assistant/chat",
                json={"message": "What is anthracnose?"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "anthracnose" in data["response"].lower()
    
    def test_chat_empty_message(self, client, auth_headers):
        """Test chat with empty message."""
        response = client.post(
            "/api/assistant/chat",
            json={"message": ""},
            headers=auth_headers
        )
        
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400, 422]
    
    def test_chat_very_long_message(self, client, auth_headers):
        """Test chat with very long message."""
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(return_value={
                "response": "Processed your message.",
                "conversation_id": str(uuid4()),
                "rich_content": None,
                "tools_used": []
            })
            
            long_message = "A" * 5000
            response = client.post(
                "/api/assistant/chat",
                json={"message": long_message},
                headers=auth_headers
            )
            
            # Should handle or truncate, not crash
            assert response.status_code in [200, 400, 413]
    
    def test_chat_urdu_message(self, client, auth_headers):
        """Test chat with Urdu language message."""
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(return_value={
                "response": "اینتھراکنوز ایک فنگل بیماری ہے",
                "conversation_id": str(uuid4()),
                "rich_content": None,
                "tools_used": []
            })
            
            response = client.post(
                "/api/assistant/chat",
                json={"message": "اینتھراکنوز کیا ہے؟"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
    
    def test_chat_service_error(self, client, auth_headers):
        """Test chat when service throws an error."""
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(side_effect=Exception("Service unavailable"))
            
            response = client.post(
                "/api/assistant/chat",
                json={"message": "Hello"},
                headers=auth_headers
            )
            
            assert response.status_code == 500


# ============================================================================
# TEST: CONVERSATIONS ENDPOINT
# ============================================================================

class TestConversationsEndpoint:
    """Tests for GET /api/assistant/conversations"""
    
    def test_get_conversations_requires_auth(self, client):
        """Test that conversations endpoint requires authentication."""
        response = client.get("/api/assistant/conversations")
        assert response.status_code in [401, 403]
    
    def test_get_conversations_success(self, client, auth_headers):
        """Test successful retrieval of user conversations."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                {
                    "id": str(uuid4()),
                    "title": "Disease Discussion",
                    "created_at": "2026-02-13T10:00:00Z",
                    "updated_at": "2026-02-13T10:30:00Z"
                }
            ]
            
            response = client.get(
                "/api/assistant/conversations",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)
    
    def test_get_conversations_empty(self, client, auth_headers):
        """Test getting conversations when user has none."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            
            response = client.get(
                "/api/assistant/conversations",
                headers=auth_headers
            )
            
            assert response.status_code == 200
    
    def test_get_conversations_with_pagination(self, client, auth_headers):
        """Test conversations endpoint with pagination."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
            
            response = client.get(
                "/api/assistant/conversations?limit=10&offset=0",
                headers=auth_headers
            )
            
            assert response.status_code == 200


# ============================================================================
# TEST: SINGLE CONVERSATION ENDPOINT
# ============================================================================

class TestSingleConversationEndpoint:
    """Tests for GET/DELETE /api/assistant/conversations/{id}"""
    
    def test_get_conversation_success(self, client, auth_headers):
        """Test successful retrieval of single conversation."""
        conversation_id = str(uuid4())
        
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {
                    "id": conversation_id,
                    "title": "Test Conversation",
                    "messages": [
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi there!"}
                    ],
                    "created_at": "2026-02-13T10:00:00Z"
                }
            ]
            
            response = client.get(
                f"/api/assistant/conversations/{conversation_id}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
    
    def test_get_conversation_not_found(self, client, auth_headers):
        """Test getting non-existent conversation."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            
            response = client.get(
                f"/api/assistant/conversations/{uuid4()}",
                headers=auth_headers
            )
            
            assert response.status_code == 404
    
    def test_get_conversation_not_owned(self, client, auth_headers):
        """Test accessing conversation owned by another user."""
        # This should return 404 (not 403) to not leak existence
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            
            response = client.get(
                f"/api/assistant/conversations/{uuid4()}",
                headers=auth_headers
            )
            
            assert response.status_code == 404
    
    def test_delete_conversation_success(self, client, auth_headers):
        """Test successful conversation deletion."""
        conversation_id = str(uuid4())
        
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            # First verify ownership
            mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": conversation_id}
            ]
            # Then delete
            mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [{}]
            
            response = client.delete(
                f"/api/assistant/conversations/{conversation_id}",
                headers=auth_headers
            )
            
            assert response.status_code in [200, 204]
    
    def test_delete_conversation_not_found(self, client, auth_headers):
        """Test deleting non-existent conversation."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            
            response = client.delete(
                f"/api/assistant/conversations/{uuid4()}",
                headers=auth_headers
            )
            
            assert response.status_code == 404


# ============================================================================
# TEST: MRL CHECK ENDPOINT
# ============================================================================

class TestMRLCheckEndpoint:
    """Tests for POST /api/assistant/mrl-check"""
    
    def test_mrl_check_success(self, client, auth_headers):
        """Test successful MRL compliance check."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.ilike.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = [
                {
                    "pesticide_name": "Carbendazim",
                    "fruit_type": "mango",
                    "country_code": "EU",
                    "mrl_value": 0.1,
                    "unit": "mg/kg"
                }
            ]
            
            response = client.post(
                "/api/assistant/mrl-check",
                json={
                    "pesticide": "Carbendazim",
                    "fruit": "mango",
                    "country": "EU"
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "mrl_value" in data or "mrl_limit" in data or "limit" in str(data).lower()
    
    def test_mrl_check_not_found(self, client, auth_headers):
        """Test MRL check when no data exists."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.ilike.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = []
            
            response = client.post(
                "/api/assistant/mrl-check",
                json={
                    "pesticide": "Unknown",
                    "fruit": "mango",
                    "country": "EU"
                },
                headers=auth_headers
            )
            
            # Should return 200 with "not found" info or 404
            assert response.status_code in [200, 404]
    
    def test_mrl_check_missing_params(self, client, auth_headers):
        """Test MRL check with missing parameters."""
        response = client.post(
            "/api/assistant/mrl-check",
            json={"pesticide": "Carbendazim"},  # Missing fruit and country
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error


# ============================================================================
# TEST: EXPORT REQUIREMENTS ENDPOINT
# ============================================================================

class TestExportRequirementsEndpoint:
    """Tests for POST /api/assistant/export-requirements"""
    
    def test_export_requirements_success(self, client, auth_headers):
        """Test successful export requirements retrieval."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = [
                {
                    "country_code": "EU",
                    "country_name": "European Union",
                    "fruit_type": "mango",
                    "phytosanitary_requirements": ["Certificate required"],
                    "certifications_needed": ["GlobalGAP"]
                }
            ]
            
            response = client.post(
                "/api/assistant/export-requirements",
                json={
                    "country": "EU",
                    "fruit": "mango"
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
    
    def test_export_requirements_not_found(self, client, auth_headers):
        """Test export requirements when not available."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.ilike.return_value.ilike.return_value.execute.return_value.data = []
            
            response = client.post(
                "/api/assistant/export-requirements",
                json={
                    "country": "Unknown",
                    "fruit": "unknown"
                },
                headers=auth_headers
            )
            
            assert response.status_code in [200, 404]


# ============================================================================
# TEST: WEB SEARCH ENDPOINT
# ============================================================================

class TestWebSearchEndpoint:
    """Tests for POST /api/assistant/web-search"""
    
    def test_web_search_success(self, client, auth_headers):
        """Test successful web search."""
        with patch('src.services.ai_agent.tavily_client.TavilyClient') as MockTavily:
            instance = MockTavily.return_value
            instance.search = AsyncMock(return_value=[
                {
                    "title": "Mango Prices in Pakistan",
                    "url": "https://example.com/article",
                    "content": "Current mango prices..."
                }
            ])
            
            response = client.post(
                "/api/assistant/web-search",
                json={"query": "mango prices Pakistan 2026"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
    
    def test_web_search_empty_query(self, client, auth_headers):
        """Test web search with empty query."""
        response = client.post(
            "/api/assistant/web-search",
            json={"query": ""},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 422]


# ============================================================================
# TEST: RESPONSE FORMAT VALIDATION
# ============================================================================

class TestResponseFormatValidation:
    """Tests for response schema validation."""
    
    def test_chat_response_schema(self, client, auth_headers):
        """Test that chat response follows expected schema."""
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(return_value={
                "response": "Test response",
                "conversation_id": str(uuid4()),
                "rich_content": None,
                "tools_used": [],
                "actions": []
            })
            
            response = client.post(
                "/api/assistant/chat",
                json={"message": "Test"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Validate required fields
            assert "response" in data
            assert "conversation_id" in data
            assert isinstance(data["response"], str)
    
    def test_conversations_list_schema(self, client, auth_headers):
        """Test that conversations list follows expected schema."""
        with patch('src.core.supabase_client.admin_supabase') as mock_db:
            mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                {
                    "id": str(uuid4()),
                    "title": "Test",
                    "created_at": "2026-02-13T10:00:00Z",
                    "updated_at": "2026-02-13T10:00:00Z"
                }
            ]
            
            response = client.get(
                "/api/assistant/conversations",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should be a list or object containing list
            assert isinstance(data, (list, dict))


# ============================================================================
# TEST: RATE LIMITING
# ============================================================================

class TestRateLimiting:
    """Tests for API rate limiting."""
    
    def test_rapid_requests(self, client, auth_headers):
        """Test handling of rapid sequential requests."""
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(return_value={
                "response": "Response",
                "conversation_id": str(uuid4())
            })
            
            # Send multiple rapid requests
            responses = []
            for i in range(10):
                response = client.post(
                    "/api/assistant/chat",
                    json={"message": f"Message {i}"},
                    headers=auth_headers
                )
                responses.append(response.status_code)
            
            # Most should succeed (429 acceptable for rate limiting)
            success_count = sum(1 for code in responses if code == 200)
            assert success_count >= 5  # At least half should succeed


# ============================================================================
# TEST: SECURITY
# ============================================================================

class TestSecurity:
    """Security-related tests."""
    
    def test_invalid_token(self, client):
        """Test with invalid authentication token."""
        response = client.post(
            "/api/assistant/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_expired_token(self, client):
        """Test with expired token."""
        # Create an expired token
        from src.core.security import create_user_token
        import time
        
        # This should be handled by the auth system
        response = client.post(
            "/api/assistant/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer expired.token.here"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_sql_injection_attempt(self, client, auth_headers):
        """Test that SQL injection attempts are handled safely."""
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(return_value={
                "response": "I cannot process that.",
                "conversation_id": str(uuid4())
            })
            
            malicious_message = "'; DROP TABLE users; --"
            
            response = client.post(
                "/api/assistant/chat",
                json={"message": malicious_message},
                headers=auth_headers
            )
            
            # Should not crash, should handle safely
            assert response.status_code in [200, 400]
    
    def test_xss_attempt_in_message(self, client, auth_headers):
        """Test that XSS attempts are handled."""
        with patch('src.api.ai_assistant.AIAgentService') as MockService:
            instance = MockService.return_value
            instance.process_message = AsyncMock(return_value={
                "response": "Response",
                "conversation_id": str(uuid4())
            })
            
            xss_message = "<script>alert('xss')</script>"
            
            response = client.post(
                "/api/assistant/chat",
                json={"message": xss_message},
                headers=auth_headers
            )
            
            assert response.status_code in [200, 400]
