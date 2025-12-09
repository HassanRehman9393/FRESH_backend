# FRESH Backend Testing Guide

## 📋 Overview

Comprehensive testing suite for the FRESH Backend API using pytest and FastAPI TestClient. This guide covers unit tests, integration tests, and best practices for testing all backend modules.

## 🏗️ Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures and configuration
├── unit/                       # Unit tests (fast, isolated)
│   ├── test_auth.py           # Authentication tests
│   ├── test_detection.py      # Fruit detection tests
│   ├── test_disease.py        # Disease detection tests
│   ├── test_weather.py        # Weather service tests
│   ├── test_orchards.py       # Orchard CRUD tests
│   ├── test_images.py         # Image handling tests
│   └── test_alerts.py         # Alert system tests
└── integration/                # Integration tests (slower, cross-module)
    └── test_workflows.py      # End-to-end workflow tests
```

## 🚀 Quick Start

### 1. Install Test Dependencies

```bash
# Install development dependencies
pip install -r requirements-dev.txt
```

### 2. Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html
```

### 3. Run Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run specific module tests
pytest -m auth
pytest -m detection
pytest -m weather
```

### 4. Run Specific Test Files

```bash
# Run authentication tests
pytest tests/unit/test_auth.py

# Run detection tests
pytest tests/unit/test_detection.py -v

# Run single test class
pytest tests/unit/test_auth.py::TestSignupUser

# Run single test
pytest tests/unit/test_auth.py::TestSignupUser::test_signup_success
```

## 📊 Test Coverage

### Current Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

### Coverage Goals

- **Overall**: ≥ 80%
- **Critical modules** (auth, detection, disease): ≥ 90%
- **API endpoints**: ≥ 85%
- **Services**: ≥ 85%

## 🧪 Test Categories

### Unit Tests (Fast, Isolated)

Unit tests focus on individual functions, methods, and classes in isolation.

**Markers**:
- `@pytest.mark.unit` - General unit test
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.detection` - Detection tests
- `@pytest.mark.disease` - Disease detection tests
- `@pytest.mark.weather` - Weather tests
- `@pytest.mark.orchards` - Orchard tests
- `@pytest.mark.images` - Image tests
- `@pytest.mark.alerts` - Alert tests

**Example**:
```python
@pytest.mark.unit
@pytest.mark.auth
def test_signup_success(test_user_data):
    """Test successful user signup"""
    # Test implementation
```

### Integration Tests (Slower, Cross-Module)

Integration tests verify interactions between multiple modules and services.

**Markers**:
- `@pytest.mark.integration` - Integration test
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_ml_api` - Requires ML API
- `@pytest.mark.requires_db` - Requires database

**Example**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_workflow(async_client):
    """Test end-to-end user workflow"""
    # Test implementation
```

## 🔧 Fixtures

### Application Fixtures

- `client` - Synchronous test client
- `async_client` - Async test client
- `event_loop` - Async event loop

### Authentication Fixtures

- `test_user_data` - Standard test user
- `auth_token` - Valid JWT token
- `auth_headers` - Headers with auth token
- `mock_current_user` - Mocked authenticated user
- `override_get_current_user` - Override auth dependency

### Data Fixtures

- `test_orchard_data` - Test orchard data
- `test_image_data` - Test image data
- `test_detection_data` - Test detection result
- `test_weather_data` - Test weather data

### Mock Fixtures

- `mock_supabase` - Mocked Supabase client
- `mock_ml_client` - Mocked ML API client
- `mock_weather_api` - Mocked weather API
- `mock_redis` - Mocked Redis client
- `mock_email_service` - Mocked email service
- `mock_upload_file` - Mocked file upload

## 📝 Writing Tests

### Test Naming Convention

```python
# Good: Descriptive, action-oriented
def test_signup_success()
def test_login_with_invalid_credentials()
def test_detect_fruit_from_image()

# Bad: Vague, unclear
def test_auth()
def test_api()
def test_function()
```

### Test Structure (AAA Pattern)

```python
def test_example():
    # Arrange - Set up test data and mocks
    user_data = {"email": "test@example.com"}
    
    # Act - Execute the function/endpoint
    result = signup_user(user_data)
    
    # Assert - Verify the results
    assert result.email == "test@example.com"
    assert result.access_token is not None
```

### Testing API Endpoints

```python
def test_api_endpoint(client, auth_headers):
    """Test API endpoint with authentication"""
    response = client.post(
        "/api/endpoint",
        headers=auth_headers,
        json={"key": "value"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "expected_key" in data
```

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function"""
    result = await async_function()
    assert result is not None
```

### Mocking Dependencies

```python
def test_with_mocked_dependency():
    """Test with mocked external dependency"""
    with patch('module.dependency') as mock_dep:
        mock_dep.return_value = {"data": "value"}
        
        result = function_using_dependency()
        
        assert result is not None
        mock_dep.assert_called_once()
```

## 🎯 Best Practices

### 1. **Test Isolation**
- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 2. **Mock External Services**
- Mock database calls
- Mock ML API calls
- Mock weather API calls
- Mock email service

### 3. **Test Edge Cases**
- Test with valid data
- Test with invalid data
- Test with missing data
- Test error conditions

### 4. **Use Parametrize for Multiple Cases**

```python
@pytest.mark.parametrize("email,expected", [
    ("valid@example.com", True),
    ("invalid-email", False),
    ("", False),
])
def test_email_validation(email, expected):
    result = validate_email(email)
    assert result == expected
```

### 5. **Test Both Success and Failure**

```python
def test_operation_success():
    """Test successful operation"""
    result = perform_operation(valid_data)
    assert result.success is True

def test_operation_failure():
    """Test operation failure"""
    with pytest.raises(ValidationError):
        perform_operation(invalid_data)
```

## 🔍 Debugging Tests

### Run Tests with Debugging

```bash
# Run tests with print statements visible
pytest -s

# Run tests with very verbose output
pytest -vv

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Run failed tests first
pytest --ff
```

### Using pytest Debugger

```python
def test_with_debugger():
    """Test with breakpoint"""
    result = function_to_test()
    
    # Add breakpoint
    import pdb; pdb.set_trace()
    
    assert result is not None
```

### View Test Output

```bash
# Show local variables on failure
pytest -l

# Show captured output on failure
pytest --capture=no
```

## 📈 Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## 🐛 Common Issues

### Issue: Tests fail with import errors

**Solution**: Ensure you're in the correct directory and have installed dependencies
```bash
cd FRESH_backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Issue: Async tests don't run

**Solution**: Install pytest-asyncio
```bash
pip install pytest-asyncio
```

### Issue: Fixtures not found

**Solution**: Check that `conftest.py` is in the correct location and properly configured

### Issue: Database tests fail

**Solution**: Use mocked database or set up test database URL
```python
@pytest.fixture
def test_db():
    # Setup test database
    yield
    # Teardown test database
```

## 📚 Module-Specific Testing

### Authentication Tests

**Coverage**:
- ✅ User signup (success, duplicate email, missing password)
- ✅ User login (success, wrong password, non-existent user)
- ✅ Google OAuth (URL generation, token verification, callback)
- ✅ JWT token generation and validation

**Run**: `pytest tests/unit/test_auth.py -v`

### Detection Tests

**Coverage**:
- ✅ Single image detection
- ✅ Batch image detection
- ✅ Detection result retrieval
- ✅ ML API timeout handling
- ✅ Bounding box validation

**Run**: `pytest tests/unit/test_detection.py -v`

### Disease Tests

**Coverage**:
- ✅ Disease detection on fruits
- ✅ Healthy fruit detection
- ✅ Diseased fruits filtering
- ✅ Severity classification

**Run**: `pytest tests/unit/test_disease.py -v`

### Weather Tests

**Coverage**:
- ✅ Current weather fetching
- ✅ Weather forecast retrieval
- ✅ Weather history
- ✅ Caching mechanism
- ✅ API error handling

**Run**: `pytest tests/unit/test_weather.py -v`

### Orchards Tests

**Coverage**:
- ✅ Create orchard
- ✅ Get user orchards
- ✅ Update orchard
- ✅ Delete orchard (soft delete)
- ✅ Coordinate validation
- ✅ Ownership verification

**Run**: `pytest tests/unit/test_orchards.py -v`

### Images Tests

**Coverage**:
- ✅ Image upload
- ✅ Batch upload
- ✅ Image retrieval
- ✅ Image deletion
- ✅ File type validation
- ✅ File size validation

**Run**: `pytest tests/unit/test_images.py -v`

### Alerts Tests

**Coverage**:
- ✅ Alert creation
- ✅ Alert filtering (severity, status, orchard)
- ✅ Alert acknowledgment
- ✅ Email notifications
- ✅ Pagination

**Run**: `pytest tests/unit/test_alerts.py -v`

### Integration Tests

**Coverage**:
- ✅ Complete user workflow
- ✅ Orchard + Weather integration
- ✅ Image → Detection → Disease workflow
- ✅ Weather → Alert workflow
- ✅ Performance tests
- ✅ Error handling

**Run**: `pytest tests/integration/ -v`

## 🎓 Learning Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python Testing Best Practices](https://realpython.com/pytest-python-testing/)

## 💡 Tips for Success

1. **Run tests frequently** during development
2. **Write tests first** (TDD approach)
3. **Keep tests simple** and focused
4. **Use descriptive names** for tests
5. **Mock external dependencies** to keep tests fast
6. **Aim for high coverage** but focus on quality
7. **Review test failures** carefully
8. **Update tests** when code changes

## 📞 Support

For questions or issues with testing:
1. Check this README first
2. Review test examples in `tests/` directory
3. Consult pytest documentation
4. Ask the development team

---

**Happy Testing! 🚀**
