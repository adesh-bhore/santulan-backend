"""
Cleanup test commuters from database
Run this before testing surge detection
"""

from app.database.db import SessionLocal
from app.drt.models import Commuter, CommuterPing, SurgeEvent

def cleanup_test_commuters():
    """Delete test commuters and their data"""
    db = SessionLocal()
    try:
        # Delete test commuters (phone numbers starting with 9000000)
        test_commuters = db.query(Commuter).filter(
            Commuter.phone.like('9000000%')
        ).all()
        
        print(f"Found {len(test_commuters)} test commuters")
        
        if test_commuters:
            commuter_ids = [c.commuter_id for c in test_commuters]
            
            # Delete their pings
            pings_deleted = db.query(CommuterPing).filter(
                CommuterPing.commuter_id.in_(commuter_ids)
            ).delete(synchronize_session=False)
            
            # Delete commuters
            commuters_deleted = db.query(Commuter).filter(
                Commuter.phone.like('9000000%')
            ).delete(synchronize_session=False)
            
            db.commit()
            
            print(f"✅ Deleted {commuters_deleted} test commuters")
            print(f"✅ Deleted {pings_deleted} test pings")
        else:
            print("✅ No test commuters to delete")
        
        # Also clean up all pings and surges for fresh start
        all_pings = db.query(CommuterPing).count()
        all_surges = db.query(SurgeEvent).count()
        
        if all_pings > 0 or all_surges > 0:
            print(f"\nCleaning up all pings and surges...")
            db.query(CommuterPing).delete()
            db.query(SurgeEvent).delete()
            db.commit()
            print(f"✅ Deleted {all_pings} pings and {all_surges} surges")
        
        print("\n✅ Cleanup complete! Ready for testing.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🗑️  Cleaning up test commuters...")
    cleanup_test_commuters()
