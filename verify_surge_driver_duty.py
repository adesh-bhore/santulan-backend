#!/usr/bin/env python3
"""
Verification script for surge driver duty fix
Checks database state and tests duty service logic
"""

import sys
from datetime import date
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, '/var/www/santulan-backend/santulan-backend')

from app.database.db import SessionLocal
from app.services.duty_service import DutyService
from app.models.base_models import Driver, Vehicle
from app.drt.models import UnscheduledTrip


def main():
    print("🔍 Verifying Surge Driver Duty Fix")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 1. Check if migration 007 was applied
        print("\n1️⃣ Checking migration status...")
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'drivers' AND column_name = 'is_surge_driver'
        """)).fetchone()
        
        if result:
            print("   ✅ Migration 007 applied (is_surge_driver column exists)")
        else:
            print("   ❌ Migration 007 NOT applied (is_surge_driver column missing)")
            print("   Run: alembic upgrade head")
            return
        
        # 2. Check surge drivers
        print("\n2️⃣ Checking surge drivers...")
        surge_drivers = db.query(Driver).filter(Driver.is_surge_driver == True).all()
        print(f"   Found {len(surge_drivers)} surge drivers:")
        for driver in surge_drivers[:5]:  # Show first 5
            print(f"   - {driver.driver_id}: {driver.driver_name} (Depot: {driver.depot_id})")
        if len(surge_drivers) > 5:
            print(f"   ... and {len(surge_drivers) - 5} more")
        
        if len(surge_drivers) == 0:
            print("   ⚠️  No surge drivers found. Run: python3 upload_surge_resources.py")
        
        # 3. Check surge vehicles
        print("\n3️⃣ Checking surge vehicles...")
        surge_vehicles = db.query(Vehicle).filter(Vehicle.is_surge_vehicle == True).all()
        print(f"   Found {len(surge_vehicles)} surge vehicles:")
        for vehicle in surge_vehicles[:5]:  # Show first 5
            print(f"   - {vehicle.vehicle_id}: {vehicle.vehicle_type} (Depot: {vehicle.depot_id})")
        if len(surge_vehicles) > 5:
            print(f"   ... and {len(surge_vehicles) - 5} more")
        
        if len(surge_vehicles) == 0:
            print("   ⚠️  No surge vehicles found. Run: python3 upload_surge_resources.py")
        
        # 4. Check unscheduled trips
        print("\n4️⃣ Checking unscheduled trips...")
        unscheduled_trips = db.query(UnscheduledTrip).all()
        print(f"   Found {len(unscheduled_trips)} unscheduled trips:")
        for trip in unscheduled_trips:
            print(f"   - Trip {trip.unscheduled_trip_id}: {trip.driver_id} -> {trip.start_stop_id} to {trip.end_stop_id}")
            print(f"     Scheduled: {trip.scheduled_start_time} | Status: {trip.status}")
        
        if len(unscheduled_trips) == 0:
            print("   ℹ️  No unscheduled trips found (this is OK if no surge events approved)")
        
        # 5. Test duty service for surge driver
        print("\n5️⃣ Testing duty service for surge driver...")
        if surge_drivers:
            test_driver_id = surge_drivers[0].driver_id
            print(f"   Testing with driver: {test_driver_id}")
            
            duty_data = DutyService.get_today_duty(db, test_driver_id)
            
            if duty_data:
                print(f"   ✅ Duty found:")
                print(f"      Route: {duty_data['duty']['routeNumber']}")
                print(f"      Vehicle: {duty_data['duty']['vehicleNumber']}")
                print(f"      Total trips: {duty_data['duty']['totalTrips']}")
                print(f"      Schedule items: {len(duty_data['schedule'])}")
                
                if duty_data['duty']['routeNumber'] == 'SURGE':
                    print("   ✅ Correctly shows as SURGE route")
                else:
                    print("   ⚠️  Expected route='SURGE' for surge driver")
                
                # Check if all trips are unscheduled
                unscheduled_count = sum(1 for trip in duty_data['schedule'] if trip.get('is_unscheduled'))
                print(f"      Unscheduled trips: {unscheduled_count}/{len(duty_data['schedule'])}")
                
                if unscheduled_count == len(duty_data['schedule']):
                    print("   ✅ All trips are unscheduled (correct for surge driver)")
                else:
                    print("   ⚠️  Surge driver should only see unscheduled trips")
            else:
                print(f"   ℹ️  No duty assigned (this is OK if no unscheduled trips for today)")
        else:
            print("   ⚠️  No surge drivers to test")
        
        # 6. Check specific surge driver from user query
        print("\n6️⃣ Checking specific surge driver: SURGE_DRV_SWGT_001...")
        specific_driver = db.query(Driver).filter(Driver.driver_id == 'SURGE_DRV_SWGT_001').first()
        
        if specific_driver:
            print(f"   ✅ Driver found: {specific_driver.driver_name}")
            print(f"      Is surge driver: {specific_driver.is_surge_driver}")
            print(f"      Depot: {specific_driver.depot_id}")
            
            # Check for unscheduled trips
            driver_trips = db.query(UnscheduledTrip).filter(
                UnscheduledTrip.driver_id == 'SURGE_DRV_SWGT_001'
            ).all()
            
            print(f"      Unscheduled trips: {len(driver_trips)}")
            for trip in driver_trips:
                print(f"      - Trip {trip.unscheduled_trip_id}: {trip.start_stop_id} -> {trip.end_stop_id}")
                print(f"        Time: {trip.scheduled_start_time}")
                print(f"        Status: {trip.status}")
            
            # Test duty service
            duty_data = DutyService.get_today_duty(db, 'SURGE_DRV_SWGT_001')
            if duty_data:
                print(f"   ✅ Duty service returns data:")
                print(f"      Route: {duty_data['duty']['routeNumber']}")
                print(f"      Trips: {duty_data['duty']['totalTrips']}")
            else:
                print(f"   ℹ️  No duty for today (check if trip is scheduled for today)")
        else:
            print("   ❌ Driver SURGE_DRV_SWGT_001 not found")
            print("      Run: python3 upload_surge_resources.py")
        
        print("\n" + "=" * 60)
        print("✅ Verification complete!")
        print("\n📋 Summary:")
        print(f"   - Surge drivers: {len(surge_drivers)}")
        print(f"   - Surge vehicles: {len(surge_vehicles)}")
        print(f"   - Unscheduled trips: {len(unscheduled_trips)}")
        
        if len(surge_drivers) == 16 and len(surge_vehicles) == 16:
            print("\n✅ All surge resources uploaded correctly!")
        else:
            print("\n⚠️  Expected 16 surge drivers and 16 surge vehicles")
            print("   Run: python3 upload_surge_resources.py")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
