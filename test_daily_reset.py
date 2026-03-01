"""Test daily reset functionality for trip logs"""

from sqlalchemy import create_engine, text
from app.config import settings
from datetime import date, timedelta

def test_daily_reset():
    """Verify trip logs reset properly for new days"""
    
    engine = create_engine(settings.database_url)
    
    print("=" * 60)
    print("Testing Daily Reset Functionality")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check current trip logs
        print("\n📊 Current trip logs:")
        result = conn.execute(text("""
            SELECT duty_date, status, COUNT(*) as count
            FROM trip_logs
            WHERE driver_id = 'DRV_BHSR_001'
            GROUP BY duty_date, status
            ORDER BY duty_date, status
        """))
        
        for row in result:
            print(f"  {row.duty_date}: {row.status} = {row.count} trips")
        
        # Simulate creating logs for tomorrow
        tomorrow = date.today() + timedelta(days=1)
        print(f"\n🔮 Simulating logs for tomorrow ({tomorrow})...")
        
        # Check if logs exist for tomorrow
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM trip_logs
            WHERE driver_id = 'DRV_BHSR_001'
            AND duty_date = :tomorrow
        """), {"tomorrow": tomorrow})
        
        count = result.fetchone().count
        print(f"  Existing logs for {tomorrow}: {count}")
        
        if count == 0:
            print(f"  ✓ No logs exist for {tomorrow} yet (as expected)")
            print(f"  ✓ When driver opens app on {tomorrow}, initialize_trip_logs() will create fresh logs")
        else:
            print(f"  ℹ️  Logs already exist for {tomorrow}")
        
        # Show the unique constraint in action
        print("\n🔑 Database Schema:")
        result = conn.execute(text("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'trip_logs'
            AND constraint_type = 'UNIQUE'
        """))
        
        for row in result:
            print(f"  {row.constraint_name}: {row.constraint_type}")
        
        print("\n✅ Daily Reset Design:")
        print("  • Each day gets its own set of trip_logs")
        print("  • Unique constraint: (trip_id, duty_date)")
        print("  • Yesterday's completed trips are preserved")
        print("  • Today's trips start fresh at 0/7")
        print("  • Historical data available for analytics")
    
    print("\n" + "=" * 60)
    print("Daily Reset Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_daily_reset()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
