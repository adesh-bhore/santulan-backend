"""Test Plan Management API Routes

Test all plan management endpoints.
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"


def test_list_plans():
    """Test GET /api/plans"""
    print("\n" + "="*60)
    print("Test 1: List Plans")
    print("="*60)
    
    # Test without filters
    response = requests.get(f"{BASE_URL}/plans")
    print(f"\nGET /api/plans")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total plans: {data['total']}")
        print(f"Showing {len(data['plans'])} plans")
        
        if data['plans']:
            print(f"\nFirst plan:")
            plan = data['plans'][0]
            print(f"  Plan ID: {plan['plan_id']}")
            print(f"  Version: {plan['version']}")
            print(f"  Depot: {plan['depot_id']}")
            print(f"  Status: {plan['status']}")
            print(f"  Fleet Size: {plan['metrics']['fleet_size']}")
            print(f"  Trips: {plan['metrics']['trips_covered']}/{plan['metrics']['trips_total']}")
        
        print(f"\n✅ List plans test passed")
        return data['plans'][0]['plan_id'] if data['plans'] else None
    else:
        print(f"❌ Failed: {response.text}")
        return None


def test_list_plans_with_filters():
    """Test GET /api/plans with filters"""
    print("\n" + "="*60)
    print("Test 2: List Plans with Filters")
    print("="*60)
    
    # Test with depot filter
    response = requests.get(f"{BASE_URL}/plans?depot_id=DEPOT_BHSR&status=PENDING&limit=5")
    print(f"\nGET /api/plans?depot_id=DEPOT_BHSR&status=PENDING&limit=5")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total plans: {data['total']}")
        print(f"✅ Filtered list test passed")
    else:
        print(f"❌ Failed: {response.text}")


def test_get_active_plans():
    """Test GET /api/plans/active"""
    print("\n" + "="*60)
    print("Test 3: Get Active Plans")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/plans/active")
    print(f"\nGET /api/plans/active")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total active plans: {data['total']}")
        
        for plan in data['active_plans']:
            print(f"\n  Depot: {plan['depot_name']} ({plan['depot_id']})")
            print(f"  Plan: version {plan['version']}")
            print(f"  Fleet Size: {plan['metrics']['fleet_size']}")
            print(f"  Deployed: {plan['deployed_at']}")
        
        print(f"\n✅ Active plans test passed")
    else:
        print(f"❌ Failed: {response.text}")


def test_get_plan_details(plan_id):
    """Test GET /api/plans/{id}"""
    print("\n" + "="*60)
    print("Test 4: Get Plan Details")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/plans/{plan_id}")
    print(f"\nGET /api/plans/{plan_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nPlan Details:")
        print(f"  Plan ID: {data['plan_id']}")
        print(f"  Version: {data['version']}")
        print(f"  Depot: {data['depot_name']} ({data['depot_id']})")
        print(f"  Status: {data['status']}")
        print(f"  Day Type: {data['day_type']}")
        
        print(f"\nMetrics:")
        print(f"  Fleet Size: {data['metrics']['fleet_size']}")
        print(f"  Trips: {data['metrics']['trips_covered']}/{data['metrics']['trips_total']}")
        print(f"  Deadhead: {data['metrics']['total_deadhead_km']} km")
        print(f"  Emissions: {data['metrics']['estimated_emissions_kg']} kg")
        
        print(f"\nVehicle Assignments: {len(data['vehicle_assignments'])} vehicles")
        if data['vehicle_assignments']:
            vehicle = data['vehicle_assignments'][0]
            print(f"  Sample: {vehicle['vehicle_id']}")
            print(f"    Type: {vehicle['vehicle_type']}")
            print(f"    Trips: {vehicle['total_trips']}")
            print(f"    Deadhead: {vehicle['total_deadhead_km']} km")
            if vehicle['trips']:
                trip = vehicle['trips'][0]
                print(f"    First trip: {trip['route_name']} ({trip['start_time']} - {trip['end_time']})")
                print(f"      From: {trip['start_stop_name']}")
                print(f"      To: {trip['end_stop_name']}")
        
        print(f"\nDriver Assignments: {len(data['driver_assignments'])} drivers")
        if data['driver_assignments']:
            driver = data['driver_assignments'][0]
            print(f"  Sample: {driver['driver_name']} ({driver['driver_id']})")
            print(f"    Shift: {driver['shift_start']} - {driver['shift_end']}")
            print(f"    Duty Hours: {driver['total_duty_hours']}")
            print(f"    Trips: {len(driver['trips'])}")
        
        print(f"\n✅ Plan details test passed")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False


def test_compare_plans(plan_id):
    """Test GET /api/plans/{id}/compare"""
    print("\n" + "="*60)
    print("Test 5: Compare Plans")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/plans/{plan_id}/compare")
    print(f"\nGET /api/plans/{plan_id}/compare")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nComparison:")
        print(f"  Plan A: {data['plan_a']['plan_id']} (version {data['plan_a']['version']})")
        print(f"  Plan B: {data['plan_b']['plan_id']} (version {data['plan_b']['version']})")
        
        print(f"\nDifferences:")
        for key, value in data['differences'].items():
            sign = "+" if value > 0 else ""
            print(f"  {key}: {sign}{value}")
        
        print(f"\n✅ Compare plans test passed")
    else:
        print(f"❌ Failed: {response.text}")


def test_deploy_plan():
    """Test POST /api/plans/{id}/deploy"""
    print("\n" + "="*60)
    print("Test 6: Deploy Plan")
    print("="*60)
    
    # Get a PENDING plan
    response = requests.get(f"{BASE_URL}/plans?status=PENDING&limit=1")
    if response.status_code == 200:
        data = response.json()
        if data['plans']:
            plan_id = data['plans'][0]['plan_id']
            
            print(f"\nPOST /api/plans/{plan_id}/deploy")
            response = requests.post(f"{BASE_URL}/plans/{plan_id}/deploy")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\nDeployment Result:")
                print(f"  Success: {result['success']}")
                print(f"  Message: {result['message']}")
                print(f"  Depot: {result['depot_id']}")
                print(f"  Version: {result['plan_version']}")
                print(f"  Vehicle Assignments: {result['vehicle_assignments']}")
                print(f"  Driver Assignments: {result['driver_assignments']}")
                print(f"  Deployed At: {result['deployed_at']}")
                print(f"\n✅ Deploy plan test passed")
            else:
                print(f"❌ Failed: {response.text}")
        else:
            print(f"⚠️  No PENDING plans to deploy")
    else:
        print(f"❌ Failed to get plans: {response.text}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing Plan Management API Routes")
    print("="*60)
    
    # Test 1: List plans
    plan_id = test_list_plans()
    
    # Test 2: List with filters
    test_list_plans_with_filters()
    
    # Test 3: Get active plans
    test_get_active_plans()
    
    # Test 4: Get plan details
    if plan_id:
        test_get_plan_details(plan_id)
        
        # Test 5: Compare plans
        test_compare_plans(plan_id)
    
    # Test 6: Deploy plan
    test_deploy_plan()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)
