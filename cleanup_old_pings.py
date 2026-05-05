"""
Cleanup script for old DRT pings
Run this periodically to keep database clean

Usage:
    python cleanup_old_pings.py              # Delete pings older than 1 day
    python cleanup_old_pings.py --all        # Delete ALL pings (demo reset)
    python cleanup_old_pings.py --days 7     # Delete pings older than 7 days
"""

from datetime import datetime, timedelta
from app.database.db import SessionLocal
from app.drt.models import CommuterPing, SurgeEvent

def cleanup_old_pings(days_to_keep=1):
    """
    Delete pings older than specified days
    
    Args:
        days_to_keep: Number of days to keep pings (default: 1 for daily cleanup)
    """
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count pings to delete
        old_pings = db.query(CommuterPing).filter(
            CommuterPing.ping_time < cutoff_date
        ).count()
        
        print(f"Found {old_pings} pings older than {days_to_keep} days")
        
        if old_pings > 0:
            # Delete old pings
            deleted = db.query(CommuterPing).filter(
                CommuterPing.ping_time < cutoff_date
            ).delete()
            
            db.commit()
            print(f"✅ Deleted {deleted} old pings")
        else:
            print("✅ No old pings to delete")
        
        return deleted
    
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


def cleanup_old_surges(days_to_keep=1):
    """
    Delete surge events older than specified days
    
    Args:
        days_to_keep: Number of days to keep surges (default: 1 for daily cleanup)
    """
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Count surges to delete
        old_surges = db.query(SurgeEvent).filter(
            SurgeEvent.detected_at < cutoff_date
        ).count()
        
        print(f"Found {old_surges} surge events older than {days_to_keep} days")
        
        if old_surges > 0:
            # Delete old surges
            deleted = db.query(SurgeEvent).filter(
                SurgeEvent.detected_at < cutoff_date
            ).delete()
            
            db.commit()
            print(f"✅ Deleted {deleted} old surge events")
        else:
            print("✅ No old surge events to delete")
        
        return deleted
    
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


def cleanup_all_demo_data():
    """
    Delete ALL pings and surges (for demo reset)
    """
    db = SessionLocal()
    try:
        # Count current data
        ping_count = db.query(CommuterPing).count()
        surge_count = db.query(SurgeEvent).count()
        
        print(f"Current data: {ping_count} pings, {surge_count} surges")
        
        # Delete all
        db.query(CommuterPing).delete()
        db.query(SurgeEvent).delete()
        
        db.commit()
        print(f"✅ Deleted all demo data ({ping_count} pings, {surge_count} surges)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            print("🗑️  Cleaning up ALL demo data...")
            cleanup_all_demo_data()
        elif sys.argv[1] == "--days" and len(sys.argv) > 2:
            days = int(sys.argv[2])
            print(f"🗑️  Cleaning up pings and surges older than {days} days...")
            cleanup_old_pings(days_to_keep=days)
            cleanup_old_surges(days_to_keep=days)
        else:
            print("Usage:")
            print("  python cleanup_old_pings.py              # Delete pings older than 1 day")
            print("  python cleanup_old_pings.py --all        # Delete ALL pings")
            print("  python cleanup_old_pings.py --days 7     # Delete pings older than 7 days")
    else:
        print("🗑️  Daily cleanup: Deleting pings and surges older than 1 day...")
        cleanup_old_pings(days_to_keep=1)
        cleanup_old_surges(days_to_keep=1)
        print("\n💡 Tip: Use --all flag to delete ALL demo data")
