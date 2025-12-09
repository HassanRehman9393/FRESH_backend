"""
Example Test File - Best Practices Demonstration
This file shows examples of well-structured tests for reference
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from uuid import uuid4


# ============================================================================
# EXAMPLE 1: Basic Unit Test with AAA Pattern
# ============================================================================

@pytest.mark.unit
def test_example_basic_unit():
    """Example: Basic unit test using AAA pattern"""
    
    # Arrange - Set up test data
    test_input = "test@example.com"
    expected_output = "test@example.com"
    
    # Act - Execute the function
    result = test_input.lower()
    
    # Assert - Verify the results
    assert result == expected_output


# ============================================================================
# EXAMPLE 2: Testing with Fixtures
# ============================================================================

@pytest.mark.unit
def test_example_with_fixtures(test_user_data, auth_token):
    """Example: Using pytest fixtures for test data"""
    
    # Fixtures provide pre-configured test data
    assert test_user_data["email"] is not None
    assert auth_token is not None
    assert len(auth_token) > 0


# ============================================================================
# EXAMPLE 3: Testing API Endpoints
# ============================================================================

@pytest.mark.unit
def test_example_api_endpoint(client, auth_headers):
    """Example: Testing a FastAPI endpoint"""
    
    # Arrange - Prepare request data
    request_data = {
        "name": "Test Orchard",
        "latitude": 33.6844,
        "longitude": 73.0479
    }
    
    # Act - Make API request
    with patch('src.core.supabase_client.supabase') as mock_supabase:
        # Mock database response
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": str(uuid4()), **request_data}
        ]
        
        response = client.post(
            "/orchards",
            headers=auth_headers,
            json=request_data
        )
    
    # Assert - Verify response
    assert response.status_code in [201, 401, 422]


# ============================================================================
# EXAMPLE 4: Testing Async Functions
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_example_async_function():
    """Example: Testing async functions"""
    
    async def async_function():
        return {"result": "success"}
    
    # Act
    result = await async_function()
    
    # Assert
    assert result["result"] == "success"


# ============================================================================
# EXAMPLE 5: Mocking External Dependencies
# ============================================================================

@pytest.mark.unit
def test_example_with_mocks():
    """Example: Mocking external dependencies"""
    
    with patch('httpx.AsyncClient') as mock_client:
        # Arrange - Set up mock
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        
        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_async_client
        
        # Your test code here
        # The httpx.AsyncClient is now mocked


# ============================================================================
# EXAMPLE 6: Testing Exceptions
# ============================================================================

@pytest.mark.unit
def test_example_exception_handling():
    """Example: Testing that exceptions are raised correctly"""
    
    def function_that_raises():
        raise ValueError("Invalid input")
    
    # Assert that exception is raised
    with pytest.raises(ValueError) as exc_info:
        function_that_raises()
    
    # Can also check exception message
    assert "Invalid input" in str(exc_info.value)


# ============================================================================
# EXAMPLE 7: Parametrized Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("input_value,expected", [
    ("test@example.com", True),
    ("invalid-email", False),
    ("", False),
    ("test@test.co.uk", True),
])
def test_example_parametrized(input_value, expected):
    """Example: Testing multiple cases with parametrize"""
    
    def validate_email(email):
        return "@" in email and "." in email and len(email) > 5
    
    result = validate_email(input_value)
    assert result == expected


# ============================================================================
# EXAMPLE 8: Testing with Multiple Mocks
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_example_multiple_mocks():
    """Example: Using multiple mocks in one test"""
    
    with patch('src.core.supabase_client.supabase') as mock_db, \
         patch('src.services.ml_client.MLClient') as mock_ml:
        
        # Mock database
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "123", "data": "test"}
        ]
        
        # Mock ML service
        mock_ml.detect_fruits = AsyncMock(return_value={
            "detections": []
        })
        
        # Your test code using both mocks


# ============================================================================
# EXAMPLE 9: Testing Class Methods
# ============================================================================

@pytest.mark.unit
class TestExampleClass:
    """Example: Organizing related tests in a class"""
    
    def test_method_success(self):
        """Test successful operation"""
        result = True
        assert result is True
    
    def test_method_failure(self):
        """Test failure case"""
        result = False
        assert result is False
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method in class"""
        async def async_op():
            return "done"
        
        result = await async_op()
        assert result == "done"


# ============================================================================
# EXAMPLE 10: Integration Test Pattern
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_example_integration(async_client, auth_headers):
    """Example: Integration test with multiple steps"""
    
    with patch('src.core.supabase_client.supabase') as mock_db, \
         patch('src.services.ml_client.MLClient') as mock_ml:
        
        # Step 1: Create resource
        create_response = await async_client.post(
            "/api/resource",
            headers=auth_headers,
            json={"name": "Test"}
        )
        # Verify creation
        
        # Step 2: Retrieve resource
        if create_response.status_code == 201:
            resource_id = create_response.json().get("id")
            
            get_response = await async_client.get(
                f"/api/resource/{resource_id}",
                headers=auth_headers
            )
            # Verify retrieval
        
        # Step 3: Update resource
        # Step 4: Delete resource
        # etc.


# ============================================================================
# EXAMPLE 11: Testing with Custom Fixtures
# ============================================================================

@pytest.fixture
def custom_test_data():
    """Example: Creating a custom fixture for specific tests"""
    return {
        "field1": "value1",
        "field2": 42,
        "field3": True
    }


@pytest.mark.unit
def test_example_custom_fixture(custom_test_data):
    """Example: Using custom fixture"""
    assert custom_test_data["field1"] == "value1"
    assert custom_test_data["field2"] == 42


# ============================================================================
# EXAMPLE 12: Testing Data Validation
# ============================================================================

@pytest.mark.unit
def test_example_data_validation():
    """Example: Testing data validation logic"""
    
    # Test valid data
    valid_latitude = 45.5
    assert -90 <= valid_latitude <= 90
    
    # Test invalid data
    invalid_latitude = 95.0
    assert not (-90 <= invalid_latitude <= 90)
    
    # Test edge cases
    edge_case_1 = -90
    edge_case_2 = 90
    assert -90 <= edge_case_1 <= 90
    assert -90 <= edge_case_2 <= 90


# ============================================================================
# EXAMPLE 13: Testing Error Messages
# ============================================================================

@pytest.mark.unit
def test_example_error_messages():
    """Example: Verifying error messages are correct"""
    
    def validate_password(password):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        return True
    
    with pytest.raises(ValueError) as exc_info:
        validate_password("short")
    
    assert "at least 8 characters" in str(exc_info.value)


# ============================================================================
# EXAMPLE 14: Setup and Teardown
# ============================================================================

@pytest.fixture
def example_setup_teardown():
    """Example: Fixture with setup and teardown"""
    
    # Setup
    resource = {"connection": "established"}
    print("Setup: Resource created")
    
    yield resource  # Provide resource to test
    
    # Teardown
    resource["connection"] = "closed"
    print("Teardown: Resource cleaned up")


@pytest.mark.unit
def test_example_with_teardown(example_setup_teardown):
    """Example: Test using setup/teardown fixture"""
    assert example_setup_teardown["connection"] == "established"


# ============================================================================
# EXAMPLE 15: Testing with Time/Dates
# ============================================================================

@pytest.mark.unit
def test_example_with_time(freeze_time):
    """Example: Testing time-dependent code"""
    from datetime import datetime
    
    # freeze_time fixture freezes time to 2024-01-01 12:00:00
    now = datetime.utcnow()
    
    # Can make assertions about the frozen time
    assert now.year == 2024
    assert now.month == 1


# ============================================================================
# BEST PRACTICES SUMMARY
# ============================================================================

"""
✅ DO:
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Test both success and failure cases
- Mock external dependencies
- Use appropriate markers
- Include docstrings
- Keep tests isolated
- Use fixtures for reusable setup

❌ DON'T:
- Make tests dependent on each other
- Test implementation details
- Use sleep() in tests
- Forget to clean up resources
- Write tests that are too complex
- Ignore test failures
- Commit commented-out tests
- Test third-party code

📊 TEST STRUCTURE:
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Fast, isolated tests
│   └── test_*.py
└── integration/         # Cross-module tests
    └── test_*.py

🎯 COVERAGE GOALS:
- Critical modules: ≥ 90%
- General modules: ≥ 80%
- Overall: ≥ 80%

🚀 RUN TESTS:
pytest                   # All tests
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest --cov=src        # With coverage
pytest -v               # Verbose
pytest -x               # Stop on first failure
pytest --lf             # Run last failed

📚 LEARN MORE:
- tests/README.md        # Detailed testing guide
- TESTING_QUICKREF.md    # Quick reference
"""
