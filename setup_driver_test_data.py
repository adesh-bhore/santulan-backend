"""Setup test data for Driver App Phase 1

This script adds authentication fields to existing drivers for testing.
"""

import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.auth_service import AuthService

# Create database connection
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def setup_test_driver():
    """Setup test driver with authentication credentials"""
    db = SessionLocal()
    
    try:
        # Get first driver from database
        result = db.execute(text("SELECT driver_id, driver_name, depot_id FROM drivers LIMIT 1"))
        driver = result.fetchone()
        
        if not driver:
            print("❌ No drivers found in database. Please upload driver CSV first.")
            return False
        
        driver_id, driver_name, depot_id = driver
        
        # Hash password
        password_hash = AuthService.get_password_hash("test123")
        
        # Update driver with auth fields (simplified - no employee_id needed)
        update_query = text("""
            UPDATE drivers 
            SET 
                password_hash = :password_hash,
                name_marathi = :name_marathi,
                phone = :phone,
                email = :email,
                license_number = :license_number,
                rating = :rating,
                total_trips = :total_trips,
                on_time_percent = :on_time_percent,
                safety_score = :safety_score,
                is_active = true
            WHERE driver_id = :driver_id
        """)
        
        db.execute(update_query, {
            "driver_id": driver_id,
            "password_hash": password_hash,
            "name_marathi": "राजेश पाटील",
            "phone": "+91 98765 43210",
            "email": f"{driver_id}@pmpml.org",
            "license_number": "MH-12-2019-0045678",
            "rating": 4.7,
            "total_trips": 3842,
            "on_time_percent": 94.2,
            "safety_score": 97
        })
        
        db.commit()
        
        print("✅ Test driver setup complete!")
        print(f"   Driver ID: {driver_id}")
        print(f"   Driver Name: {driver_name}")
        print(f"   Password: test123")
        print(f"   Depot: {depot_id}")
        print()
        print("You can now test the Driver App APIs:")
        print("1. POST /api/auth/login")
        print(f"   Body: {{\"driverId\": \"{driver_id}\", \"password\": \"test123\"}}")
        print()
        print("2. GET /api/driver/profile")
        print("   Header: Authorization: Bearer <token>")
        print()
        print("3. GET /api/duty/today")
        print("   Header: Authorization: Bearer <token>")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up test driver: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🔧 Setting up Driver App test data...")
    print()
    
    success = setup_test_driver()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
