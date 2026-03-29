"""
Quick test script for Analytics endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8080"

def test_login():
    """Test login and get token"""
    print("🔐 Testing login...")
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Login successful")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def test_quality_analytics(token):
    """Test quality analytics endpoint"""
    print("\n📊 Testing quality analytics...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/analytics/quality",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Quality analytics retrieved successfully")
        print(f"Total detections: {data.get('total_detections')}")
        print(f"Total images: {data.get('total_images')}")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Failed to get quality analytics")
        print(f"Response: {response.text}")

def test_disease_risk(token):
    """Test disease risk analytics endpoint"""
    print("\n🦠 Testing disease risk analytics...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/analytics/disease-risk",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Disease risk analytics retrieved successfully")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Failed to get disease risk analytics")
        print(f"Response: {response.text}")

def test_summary(token):
    """Test analytics summary endpoint"""
    print("\n📈 Testing analytics summary...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/analytics/summary",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Analytics summary retrieved successfully")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Failed to get analytics summary")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 FRESH Analytics API Test Suite")
    print("=" * 60)
    
    # First, try to login
    token = test_login()
    
    if token:
        # Test all analytics endpoints
        test_quality_analytics(token)
        test_disease_risk(token)
        test_summary(token)
    else:
        print("\n❌ Cannot proceed without authentication token")
        print("Please ensure:")
        print("1. Server is running on http://localhost:8080")
        print("2. You have a test user account")
        print("3. Database is accessible")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)
