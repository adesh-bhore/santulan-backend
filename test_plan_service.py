"""Test Plan Service Integration

Test that optimization creates plans in the database.
"""

import requests
import json

# Test optimization endpoint
def test_optimization_creates_plan():
    """Test that running optimization creates a plan in the database"""
    
    url = "http://localhost:8000/api/optimization/optimize"
    
    payload = {
        "depot_id": "DEPOT_BHSR",
        "day_type": "weekday",
        "objective_weights": {
            "fleet_size": 0.4,
            "deadhead": 0.3,
            "emissions": 0.2,
            "duty_variance": 0.1
        }
    }
    
    print("Testing optimization with Plan Service...")
    print(f"Request: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload)
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse:")
        print(json.dumps(result, indent=2))
        
        # Verify plan was created
        assert "plan_id" in result, "Missing plan_id"
        assert "version" in result, "Missing version"
        assert result["status"] == "PENDING", "Plan should be PENDING"
        assert result["depot_id"] == "DEPOT_BHSR", "Wrong depot_id"
        
        print(f"\n✅ SUCCESS: Plan created with ID {result['plan_id']}, version {result['version']}")
        print(f"   Fleet size: {result['metrics']['fleet_size']} vehicles")
        print(f"   Trips covered: {result['metrics']['trips_covered']}/{result['metrics']['trips_total']}")
        print(f"   Solver time: {result['metrics']['solver_time_seconds']}s")
        
        return result
    else:
        print(f"\n❌ FAILED: {response.text}")
        return None


def test_multiple_optimizations_increment_version():
    """Test that running optimization twice increments version number"""
    
    print("\n" + "="*60)
    print("Testing version increment...")
    print("="*60)
    
    url = "http://localhost:8000/api/optimization/optimize"
    
    payload = {
        "depot_id": "DEPOT_BHSR",
        "day_type": "weekday",
        "objective_weights": {
            "fleet_size": 0.5,
            "deadhead": 0.3,
            "emissions": 0.1,
            "duty_variance": 0.1
        }
    }
    
    # First optimization
    print("\nRunning first optimization...")
    response1 = requests.post(url, json=payload)
    result1 = response1.json()
    version1 = result1.get("version")
    print(f"First plan: version {version1}")
    
    # Second optimization
    print("\nRunning second optimization...")
    response2 = requests.post(url, json=payload)
    result2 = response2.json()
    version2 = result2.get("version")
    print(f"Second plan: version {version2}")
    
    # Verify version incremented
    if version2 == version1 + 1:
        print(f"\n✅ SUCCESS: Version incremented from {version1} to {version2}")
    else:
        print(f"\n❌ FAILED: Version should be {version1 + 1}, got {version2}")


if __name__ == "__main__":
    # Test 1: Basic optimization creates plan
    result = test_optimization_creates_plan()
    
    if result:
        # Test 2: Version increment
        test_multiple_optimizations_increment_version()
