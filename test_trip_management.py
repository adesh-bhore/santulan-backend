"""Test script for Trip Management APIs"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

def test_trip_management():
    """Test the complete trip management flow"""
    
    print("=" * 60)
    print("Testing Trip Management APIs")
    print("=" * 60)
    
    # Step 1: Login
    print("\n1. Testing Login...")
    login_data = {
        "driverId": "DRV_BHSR_001",
        "password": "test123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return
    
    login_result = response.json()
    token = login_result["token"]
    print(f"✓ Login successful")
    print(f"  Driver: {login_result['driver']['name']}")
    print(f"  Token: {token[:50]}...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Step 2: Get today's duty
    print("\n2. Testing GET /api/duty/today...")
    response = requests.get(f"{BASE_URL}/duty/today", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Get duty failed: {response.text}")
        return
    
    duty_result = response.json()
    print(f"✓ Duty retrieved successfully")
    print(f"  Route: {duty_result['duty']['routeNumber']}")
    print(f"  Vehicle: {duty_result['duty']['vehicleNumber']}")
    print(f"  Total Trips: {duty_result['duty']['totalTrips']}")
    print(f"  Completed Trips: {duty_result['duty']['completedTrips']}")
    
    # Print schedule
    print(f"\n  Schedule:")
    for trip in duty_result['schedule']:
        print(f"    Trip {trip['tripNumber']}: {trip['startPoint']} → {trip['endPoint']} ({trip['startTime']}-{trip['endTime']}) - Status: {trip['status']}")
    
    if not duty_result['schedule']:
        print("  No trips in schedule")
        return
    
    # Get first trip
    first_trip = duty_result['schedule'][0]
    trip_id = first_trip['id']
    
    # Step 3: Start first trip
    print(f"\n3. Testing POST /api/trips/{trip_id}/start...")
    start_data = {
        "actualStartTime": datetime.now().isoformat() + "Z",
        "location": {
            "latitude": 18.5018,
            "longitude": 73.8636
        }
    }
    
    response = requests.post(f"{BASE_URL}/trips/{trip_id}/start", json=start_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Start trip failed: {response.text}")
        # Continue anyway to test other endpoints
    else:
        start_result = response.json()
        print(f"✓ Trip started successfully")
        print(f"  Trip ID: {start_result['trip']['id']}")
        print(f"  Status: {start_result['trip']['status']}")
        print(f"  Message: {start_result['message']}")
    
    # Step 4: Get trip details
    print(f"\n4. Testing GET /api/trips/{trip_id}...")
    response = requests.get(f"{BASE_URL}/trips/{trip_id}", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Get trip failed: {response.text}")
    else:
        trip_details = response.json()
        print(f"✓ Trip details retrieved")
        print(f"  Trip Number: {trip_details['tripNumber']}")
        print(f"  Route: {trip_details['routeNumber']}")
        print(f"  Status: {trip_details['status']}")
        print(f"  Start Point: {trip_details['startPoint']}")
        print(f"  End Point: {trip_details['endPoint']}")
    
    # Step 5: End trip
    print(f"\n5. Testing POST /api/trips/{trip_id}/end...")
    end_data = {
        "actualEndTime": datetime.now().isoformat() + "Z",
        "location": {
            "latitude": 18.5074,
            "longitude": 73.8077
        },
        "passengerCount": 45,
        "fareCollected": 1350.00,
        "notes": "Trip completed successfully"
    }
    
    response = requests.post(f"{BASE_URL}/trips/{trip_id}/end", json=end_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"End trip failed: {response.text}")
    else:
        end_result = response.json()
        print(f"✓ Trip ended successfully")
        print(f"  Trip ID: {end_result['trip']['id']}")
        print(f"  Status: {end_result['trip']['status']}")
        print(f"  Duration: {end_result['trip']['duration']} minutes")
        print(f"  Passenger Count: {end_result['trip']['passengerCount']}")
        print(f"  Fare Collected: ₹{end_result['trip']['fareCollected']}")
        print(f"  Completed Trips: {end_result['duty']['completedTrips']}/{end_result['duty']['totalTrips']}")
    
    # Step 6: Get duty again to verify state persistence
    print("\n6. Testing state persistence - GET /api/duty/today again...")
    response = requests.get(f"{BASE_URL}/duty/today", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Get duty failed: {response.text}")
    else:
        duty_result = response.json()
        print(f"✓ Duty retrieved successfully")
        print(f"  Completed Trips: {duty_result['duty']['completedTrips']}")
        print(f"\n  Updated Schedule:")
        for trip in duty_result['schedule']:
            status_icon = "✓" if trip['status'] == "completed" else ("▶" if trip['status'] == "active" else "○")
            print(f"    {status_icon} Trip {trip['tripNumber']}: {trip['startPoint']} → {trip['endPoint']} - Status: {trip['status']}")
    
    print("\n" + "=" * 60)
    print("Trip Management API Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_trip_management()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
