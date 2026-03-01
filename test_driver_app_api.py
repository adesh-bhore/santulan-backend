"""Test Driver App Phase 1 APIs

Quick test script to verify all endpoints are working.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def print_response(title, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_login():
    """Test login endpoint"""
    print("\n🔐 Testing Login...")
    
    # Get first driver from database to use their ID
    # For now, using a placeholder - update with actual driver_id
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "driverId": "DRV_BHSR_004",  # Update this with actual driver_id
            "password": "test123"
        }
    )
    
    print_response("POST /api/auth/login", response)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("token"), data.get("refreshToken")
    
    return None, None


def test_profile(token):
    """Test profile endpoint"""
    print("\n👤 Testing Profile...")
    
    response = requests.get(
        f"{BASE_URL}/api/driver/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print_response("GET /api/driver/profile", response)


def test_today_duty(token):
    """Test today's duty endpoint"""
    print("\n📋 Testing Today's Duty...")
    
    response = requests.get(
        f"{BASE_URL}/api/duty/today",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print_response("GET /api/duty/today", response)


def test_refresh_token(refresh_token):
    """Test token refresh endpoint"""
    print("\n🔄 Testing Token Refresh...")
    
    response = requests.post(
        f"{BASE_URL}/api/auth/refresh",
        json={"refreshToken": refresh_token}
    )
    
    print_response("POST /api/auth/refresh", response)
    
    if response.status_code == 200:
        return response.json().get("token")
    
    return None


def test_logout(token):
    """Test logout endpoint"""
    print("\n👋 Testing Logout...")
    
    response = requests.post(
        f"{BASE_URL}/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print_response("POST /api/auth/logout", response)


def test_invalid_credentials():
    """Test login with invalid credentials"""
    print("\n❌ Testing Invalid Credentials...")
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "driverId": "INVALID_DRIVER",
            "password": "wrong"
        }
    )
    
    print_response("POST /api/auth/login (Invalid)", response)


def test_invalid_token():
    """Test endpoint with invalid token"""
    print("\n❌ Testing Invalid Token...")
    
    response = requests.get(
        f"{BASE_URL}/api/driver/profile",
        headers={"Authorization": "Bearer invalid-token-here"}
    )
    
    print_response("GET /api/driver/profile (Invalid Token)", response)


def main():
    """Run all tests"""
    print("🧪 Driver App Phase 1 API Tests")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print("="*60)
    
    try:
        # Test 1: Login
        token, refresh_token = test_login()
        
        if not token:
            print("\n❌ Login failed. Cannot continue tests.")
            print("Make sure:")
            print("1. Backend server is running")
            print("2. Database migration is complete")
            print("3. Test data is setup (run setup_driver_test_data.py)")
            return
        
        # Test 2: Profile
        test_profile(token)
        
        # Test 3: Today's Duty
        test_today_duty(token)
        
        # Test 4: Refresh Token
        new_token = test_refresh_token(refresh_token)
        
        # Test 5: Logout
        test_logout(token if not new_token else new_token)
        
        # Test 6: Error Cases
        test_invalid_credentials()
        test_invalid_token()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error!")
        print("Make sure the backend server is running:")
        print("  cd backend")
        print("  python -m uvicorn app.main:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ Test Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
