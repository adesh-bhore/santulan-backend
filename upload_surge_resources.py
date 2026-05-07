"""
Upload surge vehicles and drivers to database
Run this after running the migration
"""

import csv
from app.database.db import SessionLocal
from app.models.base_models import Vehicle, Driver
from sqlalchemy import text

def upload_surge_vehicles():
    """Upload surge vehicles from CSV"""
    db = SessionLocal()
    try:
        print("📦 Uploading surge vehicles...")
        
        with open('CSV_DATA/surge_vehicles.csv', 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                # Check if vehicle already exists
                existing = db.query(Vehicle).filter(
                    Vehicle.vehicle_id == row['vehicle_id']
                ).first()
                
                if existing:
                    print(f"  ⚠️  Vehicle {row['vehicle_id']} already exists, skipping")
                    continue
                
                # Create vehicle
                vehicle = Vehicle(
                    vehicle_id=row['vehicle_id'],
                    vehicle_number=row['vehicle_number'],
                    vehicle_type=row['vehicle_type'],
                    capacity=int(row['capacity']),
                    depot_id=row['depot_id'],
                    status=row['status']
                )
                
                db.add(vehicle)
                count += 1
                print(f"  ✓ Added {row['vehicle_id']} - {row['vehicle_number']}")
            
            # Now update is_surge_vehicle flag
            db.execute(text("""
                UPDATE vehicles 
                SET is_surge_vehicle = true 
                WHERE vehicle_id LIKE 'SURGE_VEH_%'
            """))
            
            db.commit()
            print(f"\n✅ Uploaded {count} surge vehicles")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def upload_surge_drivers():
    """Upload surge drivers from CSV"""
    db = SessionLocal()
    try:
        print("\n👥 Uploading surge drivers...")
        
        with open('CSV_DATA/surge_drivers.csv', 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                # Check if driver already exists
                existing = db.query(Driver).filter(
                    Driver.driver_id == row['driver_id']
                ).first()
                
                if existing:
                    print(f"  ⚠️  Driver {row['driver_id']} already exists, skipping")
                    continue
                
                # Create driver
                driver = Driver(
                    driver_id=row['driver_id'],
                    name=row['name'],
                    phone=row['phone'],
                    license_number=row['license_number'],
                    depot_id=row['depot_id'],
                    status=row['status']
                )
                
                db.add(driver)
                count += 1
                print(f"  ✓ Added {row['driver_id']} - {row['name']}")
            
            # Now update is_surge_driver flag
            db.execute(text("""
                UPDATE drivers 
                SET is_surge_driver = true 
                WHERE driver_id LIKE 'SURGE_DRV_%'
            """))
            
            db.commit()
            print(f"\n✅ Uploaded {count} surge drivers")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def verify_surge_resources():
    """Verify surge resources in database"""
    db = SessionLocal()
    try:
        print("\n🔍 Verifying surge resources...")
        
        # Count surge vehicles
        surge_vehicles = db.execute(text("""
            SELECT COUNT(*) as count, depot_id 
            FROM vehicles 
            WHERE is_surge_vehicle = true 
            GROUP BY depot_id
            ORDER BY depot_id
        """)).fetchall()
        
        print("\n📦 Surge Vehicles by Depot:")
        for row in surge_vehicles:
            print(f"  {row.depot_id}: {row.count} vehicles")
        
        # Count surge drivers
        surge_drivers = db.execute(text("""
            SELECT COUNT(*) as count, depot_id 
            FROM drivers 
            WHERE is_surge_driver = true 
            GROUP BY depot_id
            ORDER BY depot_id
        """)).fetchall()
        
        print("\n👥 Surge Drivers by Depot:")
        for row in surge_drivers:
            print(f"  {row.depot_id}: {row.count} drivers")
        
        print("\n✅ Verification complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Uploading Surge Resources")
    print("=" * 50)
    
    upload_surge_vehicles()
    upload_surge_drivers()
    verify_surge_resources()
    
    print("\n" + "=" * 50)
    print("✅ All surge resources uploaded successfully!")
    print("\nNext steps:")
    print("1. Restart backend service")
    print("2. Surge approval will now show only surge vehicles/drivers")
    print("3. Surge drivers will see only surge trips in their app")
