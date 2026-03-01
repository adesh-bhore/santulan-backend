"""Reset all trip logs to scheduled status for testing"""

from sqlalchemy import create_engine, text
from app.config import settings

def reset_trip_logs():
    """Reset all trip logs to scheduled status"""
    
    # Create database connection
    engine = create_engine(settings.database_url)
    
    print("🔄 Resetting trip logs...")
    
    with engine.connect() as conn:
        # Reset all trip logs to scheduled status
        result = conn.execute(text("""
            UPDATE trip_logs 
            SET 
                status = 'scheduled',
                actual_start_time = NULL,
                actual_end_time = NULL,
                duration_minutes = NULL,
                start_location = NULL,
                end_location = NULL,
                passenger_count = NULL,
                fare_collected = NULL,
                notes = NULL,
                updated_at = NOW()
        """))
        
        conn.commit()
        
        print(f"✅ Reset {result.rowcount} trip logs to 'scheduled' status")
        
        # Show current status
        result = conn.execute(text("""
            SELECT status, COUNT(*) as count
            FROM trip_logs
            GROUP BY status
            ORDER BY status
        """))
        
        print("\n📊 Current trip log status:")
        for row in result:
            print(f"   {row.status}: {row.count}")


if __name__ == "__main__":
    try:
        reset_trip_logs()
        print("\n✓ Trip logs reset successfully!")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
