"""
Clear all data from the database in the correct order
This removes all base data, plan data, and active data
"""

from sqlalchemy import text
from app.database.db import get_db

def clear_database():
    """Clear all tables in the correct order to avoid foreign key violations"""
    db = next(get_db())
    
    try:
        print("Clearing database...")
        print("=" * 60)
        
        # Order matters! Delete in reverse order of dependencies
        tables_to_clear = [
            # Current/Active tables (depend on timetable)
            "current_vehicle_assignments",
            "current_driver_assignments",
            "current_trip_assignments",
            
            # Plan tables (depend on base tables)
            "plan_vehicle_assignments",
            "plan_driver_assignments",
            "plan_trip_assignments",
            "plans",
            
            # Base tables (in dependency order)
            "timetable",  # depends on routes and stops
            "drivers",    # depends on depots
            "vehicles",   # depends on depots
            "routes",     # depends on depots
            "stops",      # no dependencies
            "depots",     # no dependencies
        ]
        
        for table in tables_to_clear:
            print(f"Clearing {table}...", end=" ")
            try:
                db.execute(text(f"DELETE FROM {table}"))
                db.commit()
                print("✅")
            except Exception as e:
                if "does not exist" in str(e):
                    print("⏭️  (table doesn't exist)")
                    db.rollback()
                else:
                    raise
        
        print("=" * 60)
        print("✅ Database cleared successfully!")
        print("\nYou can now run: python upload_all_csv.py")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    clear_database()
