"""Test Driver App API Routes

Tests for GET /api/driver/{driver_id}/schedule endpoint.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base_models import Base, Driver, Depot, Route, Stop, Vehicle, Timetable
from app.models.plan_models import CurrentDriverAssignment, CurrentVehicleAssignment
from app.database.db import get_db
from app.api.driver_routes import router
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import time
import uuid

# Create test database (use same credentials as main database)
TEST_DATABASE_URL = "postgresql://postgres:Adesh@localhost:5432/pmpml_optimization"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test app
app = FastAPI()
app.include_router(router, prefix="/api")

# Override dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def setup_test_data():
    """Create test data in database"""
    # Drop and recreate tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    try:
        # Create depot
        depot = Depot(
            depot_id="DEPOT_TEST",
            depot_name="Test Depot",
            latitude=18.5204,
            longitude=73.8567
        )
        db.add(depot)
        
        # Create driver
        driver = Driver(
            driver_id="DRV001",
            driver_name="John Doe",
            depot_id="DEPOT_TEST",
            max_duty_hours=8.0
        )
        db.add(driver)
        
        # Create route
        route = Route(
            route_id="ROUTE_1",
            route_name="Route 1 - City Center",
            depot_id="DEPOT_TEST"
        )
        db.add(route)
        
        # Create stops
        stop1 = Stop(
            stop_id="STOP_A",
            stop_name="Stop A - Main Square",
            latitude=18.5204,
            longitude=73.8567
        )
        stop2 = Stop(
            stop_id="STOP_B",
            stop_name="Stop B - Market",
            latitude=18.5304,
            longitude=73.8667
        )
        db.add_all([stop1, stop2])
        
        # Create vehicle
        vehicle = Vehicle(
            vehicle_id="VEH001",
            vehicle_type="Standard Bus",
            capacity=50,
            depot_id="DEPOT_TEST"
        )
        db.add(vehicle)
        
        # Create timetable entries
        trip1 = Timetable(
            trip_id="TRIP_001",
            route_id="ROUTE_1",
            start_time=time(8, 0),
            end_time=time(8, 45),
            start_stop_id="STOP_A",
            end_stop_id="STOP_B",
            day_type="weekday"
        )
        trip2 = Timetable(
            trip_id="TRIP_002",
            route_id="ROUTE_1",
            start_time=time(9, 0),
            end_time=time(9, 45),
            start_stop_id="STOP_B",
            end_stop_id="STOP_A",
            day_type="weekday"
        )
        db.add_all([trip1, trip2])
        
        # Create current driver assignments
        assignment1 = CurrentDriverAssignment(
            assignment_id=uuid.uuid4(),
            depot_id="DEPOT_TEST",
            driver_id="DRV001",
            trip_id="TRIP_001",
            sequence_order=1,
            duty_hours=7.5,
            break_minutes=45
        )
        assignment2 = CurrentDriverAssignment(
            assignment_id=uuid.uuid4(),
            depot_id="DEPOT_TEST",
            driver_id="DRV001",
            trip_id="TRIP_002",
            sequence_order=2,
            duty_hours=7.5,
            break_minutes=45
        )
        db.add_all([assignment1, assignment2])
        
        # Create current vehicle assignments
        vehicle_assignment1 = CurrentVehicleAssignment(
            assignment_id=uuid.uuid4(),
            depot_id="DEPOT_TEST",
            vehicle_id="VEH001",
            trip_id="TRIP_001",
            sequence_order=1,
            deadhead_km=5.0
        )
        vehicle_assignment2 = CurrentVehicleAssignment(
            assignment_id=uuid.uuid4(),
            depot_id="DEPOT_TEST",
            vehicle_id="VEH001",
            trip_id="TRIP_002",
            sequence_order=2,
            deadhead_km=3.0
        )
        db.add_all([vehicle_assignment1, vehicle_assignment2])
        
        db.commit()
        print("✓ Test data created successfully")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Failed to create test data: {e}")
        raise
    finally:
        db.close()


def test_get_driver_schedule_with_assignments():
    """Test getting schedule for driver with assignments"""
    print("\n=== Test: Get Driver Schedule with Assignments ===")
    
    response = client.get("/api/driver/DRV001/schedule")
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    
    data = response.json()
    print(f"Response: {data}")
    
    # Verify driver information
    assert data["driver_id"] == "DRV001"
    assert data["driver_name"] == "John Doe"
    assert data["depot_id"] == "DEPOT_TEST"
    assert data["depot_name"] == "Test Depot"
    
    # Verify schedule
    assert len(data["schedule"]) == 2
    
    # Verify first trip
    trip1 = data["schedule"][0]
    assert trip1["trip_id"] == "TRIP_001"
    assert trip1["route_id"] == "ROUTE_1"
    assert trip1["route_name"] == "Route 1 - City Center"
    assert trip1["vehicle_id"] == "VEH001"
    assert trip1["vehicle_type"] == "Standard Bus"
    assert trip1["start_time"] == "08:00:00"
    assert trip1["end_time"] == "08:45:00"
    assert trip1["start_stop"] == "Stop A - Main Square"
    assert trip1["end_stop"] == "Stop B - Market"
    assert trip1["sequence_order"] == 1
    
    # Verify second trip
    trip2 = data["schedule"][1]
    assert trip2["trip_id"] == "TRIP_002"
    assert trip2["sequence_order"] == 2
    
    # Verify shift summary
    assert data["total_duty_hours"] == 7.5
    assert data["break_minutes"] == 45
    assert data["shift_start"] == "08:00:00"
    assert data["shift_end"] == "09:45:00"
    
    print("✓ Test passed: Driver schedule retrieved correctly")


def test_get_driver_schedule_no_assignments():
    """Test getting schedule for driver with no assignments"""
    print("\n=== Test: Get Driver Schedule with No Assignments ===")
    
    # Create driver without assignments
    db = TestingSessionLocal()
    driver = Driver(
        driver_id="DRV002",
        driver_name="Jane Smith",
        depot_id="DEPOT_TEST",
        max_duty_hours=8.0
    )
    db.add(driver)
    db.commit()
    db.close()
    
    response = client.get("/api/driver/DRV002/schedule")
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    
    data = response.json()
    print(f"Response: {data}")
    
    # Verify empty schedule (not an error)
    assert data["driver_id"] == "DRV002"
    assert data["driver_name"] == "Jane Smith"
    assert data["schedule"] == []
    assert data["total_duty_hours"] == 0.0
    assert data["break_minutes"] == 0
    assert data["shift_start"] is None
    assert data["shift_end"] is None
    
    print("✓ Test passed: Empty schedule returned correctly")


def test_get_driver_schedule_nonexistent_driver():
    """Test getting schedule for non-existent driver"""
    print("\n=== Test: Get Driver Schedule for Non-existent Driver ===")
    
    response = client.get("/api/driver/DRV999/schedule")
    
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200  # Not an error, returns empty schedule
    
    data = response.json()
    print(f"Response: {data}")
    
    # Verify empty schedule for non-existent driver
    assert data["driver_id"] == "DRV999"
    assert data["schedule"] == []
    
    print("✓ Test passed: Non-existent driver handled correctly")


if __name__ == "__main__":
    print("=" * 60)
    print("Driver App API Routes Test Suite")
    print("=" * 60)
    
    try:
        # Setup
        print("\nSetting up test data...")
        setup_test_data()
        
        # Run tests
        test_get_driver_schedule_with_assignments()
        test_get_driver_schedule_no_assignments()
        test_get_driver_schedule_nonexistent_driver()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ Tests failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)
