"""
Cleanup script for DRT test data

This script removes all test commuters and pings created during testing.
Use this before running a fresh test.
"""

from app.database.db import SessionLocal
from app.drt.models import Commuter, CommuterPing, SurgeEvent, UnscheduledTrip
from sqlalchemy import or_

def cleanup_test_data():
    """Remove all test data from DRT tables"""
    db = SessionLocal()
    
    try:
        print("Starting cleanup...")
        
        # Delete unscheduled trips
        unscheduled_count = db.query(UnscheduledTrip).delete()
        print(f"✓ Deleted {unscheduled_count} unscheduled trips")
        
        # Delete surge events
        surge_count = db.query(SurgeEvent).delete()
        print(f"✓ Deleted {surge_count} surge events")
        
        # Delete commuter pings
        ping_count = db.query(CommuterPing).delete()
        print(f"✓ Deleted {ping_count} commuter pings")
        
        # Delete test commuters (phone starts with 9876)
        commuter_count = db.query(Commuter).filter(
            Commuter.phone.like('9876%')
        ).delete(synchronize_session=False)
        print(f"✓ Deleted {commuter_count} test commuters")
        
        db.commit()
        print("\n✅ Cleanup complete!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Cleanup failed: {str(e)}")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("DRT TEST DATA CLEANUP")
    print("=" * 60)
    print("\nThis will delete:")
    print("- All unscheduled trips")
    print("- All surge events")
    print("- All commuter pings")
    print("- All test commuters (phone starting with 9876)")
    print()
    
    confirm = input("Continue? (y/n): ")
    
    if confirm.lower() == 'y':
        cleanup_test_data()
    else:
        print("Cleanup cancelled.")
