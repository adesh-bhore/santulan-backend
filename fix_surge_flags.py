#!/usr/bin/env python3
"""
Fix surge flags for surge drivers and vehicles
Sets is_surge_driver=true and is_surge_vehicle=true for all SURGE_* resources
"""

import sys
sys.path.insert(0, '/var/www/santulan-backend/santulan-backend')

from app.database.db import SessionLocal
from app.models.base_models import Driver, Vehicle


def fix_surge_flags():
    """Update surge flags for all surge drivers and vehicles"""
    
    db = SessionLocal()
    
    print("🔧 Fixing Surge Flags")
    print("=" * 60)
    
    try:
        # Fix surge drivers
        print("\n👥 Updating surge drivers...")
        surge_drivers = db.query(Driver).filter(
            Driver.driver_id.like('SURGE_DRV_%')
        ).all()
        
        driver_count = 0
        for driver in surge_drivers:
            driver.is_surge_driver = True
            driver_count += 1
            print(f"   ✓ {driver.driver_id} → is_surge_driver = true")
        
        # Fix surge vehicles
        print(f"\n📦 Updating surge vehicles...")
        surge_vehicles = db.query(Vehicle).filter(
            Vehicle.vehicle_id.like('SURGE_VEH_%')
        ).all()
        
        vehicle_count = 0
        for vehicle in surge_vehicles:
            vehicle.is_surge_vehicle = True
            vehicle_count += 1
            print(f"   ✓ {vehicle.vehicle_id} → is_surge_vehicle = true")
        
        # Commit changes
        db.commit()
        
        print(f"\n" + "=" * 60)
        print(f"✅ Successfully updated:")
        print(f"   - {driver_count} surge drivers")
        print(f"   - {vehicle_count} surge vehicles")
        print(f"\n📋 Verification:")
        print(f"   Run: SELECT driver_id, is_surge_driver FROM drivers WHERE driver_id LIKE 'SURGE_%';")
        print(f"   Run: SELECT vehicle_id, is_surge_vehicle FROM vehicles WHERE vehicle_id LIKE 'SURGE_%';")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    fix_surge_flags()
