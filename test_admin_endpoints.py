#!/usr/bin/env python
"""
Test script for admin endpoints
"""
import requests
import json
import uuid
from typing import Optional

BASE_URL = "http://localhost:8000/api"
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "testpassword123"

def login(email: str, password: str) -> Optional[str]:
    """Login and return access token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    print(f"❌ Login failed: {response.text}")
    return None

def create_admin_user() -> bool:
    """Create an admin user for testing"""
    response = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "full_name": "Test Admin",
            "role": "admin"
        }
    )
    if response.status_code == 201:
        print(f"✅ Admin user created: {ADMIN_EMAIL}")
        return True
    elif response.status_code == 409:
        print(f"ℹ️  Admin user already exists: {ADMIN_EMAIL}")
        return True
    else:
        print(f"❌ Failed to create admin user: {response.text}")
        return False

def test_admin_endpoints(token: str) -> None:
    """Test all admin endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n" + "="*60)
    print("TESTING ADMIN ENDPOINTS")
    print("="*60)
    
    # Test 1: Get all users
    print("\n1️⃣  Testing GET /api/admin/users")
    response = requests.get(
        f"{BASE_URL}/admin/users?limit=10&offset=0",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ Users fetched: {len(response.json())} users")
        for user in response.json()[:3]:
            print(f"   - {user['email']} ({user['role']})")
    else:
        print(f"❌ Error: {response.text}")
    
    # Test 2: Create a user
    print("\n2️⃣  Testing POST /api/admin/users")
    new_user = {
        "email": f"testuser_{str(uuid.uuid4())[:8]}@test.com",
        "password": "password123",
        "full_name": "Test User",
        "role": "farmer"
    }
    response = requests.post(
        f"{BASE_URL}/admin/users",
        json=new_user,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        created_user = response.json()
        print(f"✅ User created: {created_user['email']}")
        test_user_id = created_user['id']
    else:
        print(f"❌ Error: {response.text}")
        return
    
    # Test 3: Update a user
    print("\n3️⃣  Testing PUT /api/admin/users/{user_id}")
    update_data = {
        "full_name": "Updated Name",
        "role": "exporter"
    }
    response = requests.put(
        f"{BASE_URL}/admin/users/{test_user_id}",
        json=update_data,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        updated_user = response.json()
        print(f"✅ User updated: {updated_user['full_name']} ({updated_user['role']})")
    else:
        print(f"❌ Error: {response.text}")
    
    # Test 4: Get all orchards
    print("\n4️⃣  Testing GET /api/admin/orchards")
    response = requests.get(
        f"{BASE_URL}/admin/orchards?limit=10&offset=0",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        orchards = response.json()
        print(f"✅ Orchards fetched: {len(orchards)} orchards")
        for orchard in orchards[:3]:
            print(f"   - {orchard.get('name', 'N/A')} (user: {orchard.get('user_id', 'N/A')})")
    else:
        print(f"❌ Error: {response.text}")
    
    # Test 5: Get all detection results
    print("\n5️⃣  Testing GET /api/admin/detection-results")
    response = requests.get(
        f"{BASE_URL}/admin/detection-results?limit=10&offset=0",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        results = response.json()
        print(f"✅ Detection results fetched: {len(results)} results")
        for result in results[:3]:
            print(f"   - ID: {result.get('detection_id', 'N/A')} (fruit: {result.get('fruit_type', 'N/A')})")
    else:
        print(f"❌ Error: {response.text}")
    
    # Test 6: Delete a user
    print("\n6️⃣  Testing DELETE /api/admin/users/{user_id}")
    response = requests.delete(
        f"{BASE_URL}/admin/users/{test_user_id}",
        headers=headers
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 204:
        print(f"✅ User deleted successfully")
    else:
        print(f"❌ Error: {response.text}")

def main():
    print("🚀 Starting admin endpoint tests...\n")
    
    # Create admin user
    if not create_admin_user():
        return
    
    # Login
    print(f"\n🔐 Logging in as {ADMIN_EMAIL}...")
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not token:
        print("❌ Failed to get access token")
        return
    print(f"✅ Login successful, token: {token[:20]}...")
    
    # Test endpoints
    test_admin_endpoints(token)
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)

if __name__ == "__main__":
    main()
