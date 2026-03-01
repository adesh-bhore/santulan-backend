"""Check trip logs status for debugging"""

from sqlalchemy import create_engine, text
from app.config import settings

def check_trip_logs():
    """Check current trip logs status"""
    
    # Create database connection
    engine = create_engine(settings.database_url)
    
    print("📊 Checking trip logs...")
    
    with engine.connect() as conn:
        # Get all trip logs for driver DRV_BHSR_001
        result = conn.execute(text("""
            SELECT 
                trip_id,
                driver_id,
                duty_date,
                status,
                actual_start_time,
                actual_end_time,
                duration_minutes
            FROM trip_logs
            WHERE driver_id = 'DRV_BHSR_001'
            ORDER BY scheduled_start_time
        """))
        
        print("\n🔍 Trip logs for DRV_BHSR_001:")
        print("-" * 80)
        for row in result:
            print(f"Trip: {row.trip_id}")
            print(f"  Status: {row.status}")
            print(f"  Duty Date: {row.duty_date}")
            print(f"  Start Time: {row.actual_start_time}")
            print(f"  End Time: {row.actual_end_time}")
            print(f"  Duration: {row.duration_minutes}")
            print()


if __name__ == "__main__":
    try:
        check_trip_logs()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
