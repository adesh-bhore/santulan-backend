#!/usr/bin/env python3
"""
Add route_stops table for corridor-based clustering

This script creates the route_stops table and populates it with sample data
for demonstration purposes.
"""

from sqlalchemy import create_engine, text
from app.config import settings
from app.database.db import get_db
import csv

def create_route_stops_table():
    """Create route_stops table"""
    
    engine = create_engine(settings.database_url)
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS route_stops (
        route_stop_id SERIAL PRIMARY KEY,
        route_id VARCHAR(50) NOT NULL,
        stop_id VARCHAR(50) NOT NULL,
        stop_sequence INT NOT NULL,
        distance_from_start_km DECIMAL(10, 2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE,
        FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE CASCADE,
        UNIQUE(route_id, stop_sequence),
        UNIQUE(route_id, stop_id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_route_stops_route ON route_stops(route_id);
    CREATE INDEX IF NOT EXISTS idx_route_stops_stop ON route_stops(stop_id);
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
    
    print("✓ Created route_stops table")


def populate_sample_data():
    """Populate with sample route stop sequences"""
    
    # Sample data for demonstration
    # In production, this should come from actual route planning data
    sample_routes = [
        # Route 1: Swargate to Katraj (with all intermediate stops)
        {'route_id': '1', 'stops': [
            ('STOP_SWGT', 0.0),
            ('STOP_MRKT', 1.5),
            ('STOP_DHNK', 3.2),
            ('STOP_BIBW', 4.8),
            ('STOP_KTRJ', 6.5),
        ]},
        
        # Route 2: Swargate to Shivajinagar
        {'route_id': '2', 'stops': [
            ('STOP_SWGT', 0.0),
            ('STOP_PNST', 2.1),
            ('STOP_DCCN', 3.5),
            ('STOP_SHVJ', 4.2),
        ]},
        
        # Route 3: Swargate to Hadapsar
        {'route_id': '3', 'stops': [
            ('STOP_SWGT', 0.0),
            ('STOP_WNGV', 2.3),
            ('STOP_FTHS', 3.8),
            ('STOP_HDPS', 5.5),
        ]},
        
        # Route 4: Swargate to Kothrud
        {'route_id': '4', 'stops': [
            ('STOP_SWGT', 0.0),
            ('STOP_DCCN', 2.1),
            ('STOP_KRVE', 3.5),
            ('STOP_KTRD', 4.8),
        ]},
        
        # Route 5: Swargate to Market Yard
        {'route_id': '5', 'stops': [
            ('STOP_SWGT', 0.0),
            ('STOP_MRKT', 1.5),
        ]},
        
        # Route 6: Swargate to Deccan
        {'route_id': '6', 'stops': [
            ('STOP_SWGT', 0.0),
            ('STOP_PNST', 2.1),
            ('STOP_DCCN', 3.5),
        ]},
        
        # Route 31: Katraj to Swargate (reverse of Route 1 - COMPLETE CORRIDOR)
        {'route_id': '31', 'stops': [
            ('STOP_KTRJ', 0.0),
            ('STOP_BIBW', 1.7),
            ('STOP_DHNK', 3.3),
            ('STOP_MRKT', 5.0),
            ('STOP_SWGT', 6.5),
        ]},
        
        # Route 32: Katraj to Dhankawadi
        {'route_id': '32', 'stops': [
            ('STOP_KTRJ', 0.0),
            ('STOP_BIBW', 1.7),
            ('STOP_DHNK', 3.3),
        ]},
        
        # Route 33: Katraj to Market Yard
        {'route_id': '33', 'stops': [
            ('STOP_KTRJ', 0.0),
            ('STOP_BIBW', 1.7),
            ('STOP_DHNK', 3.3),
            ('STOP_MRKT', 5.0),
        ]},
        
        # Route 34: Katraj to Bibvewadi
        {'route_id': '34', 'stops': [
            ('STOP_KTRJ', 0.0),
            ('STOP_BIBW', 1.7),
        ]},
        
        # Hadapsar Routes (72-75) for depot detection
        {'route_id': '72', 'stops': [
            ('STOP_HDPS', 0.0),
            ('STOP_FTHS', 1.7),
            ('STOP_WNGV', 3.2),
            ('STOP_SWGT', 5.5),
        ]},
        
        {'route_id': '73', 'stops': [
            ('STOP_HDPS', 0.0),
            ('STOP_MNDW', 2.5),
            ('STOP_KHRD', 4.8),
        ]},
        
        {'route_id': '74', 'stops': [
            ('STOP_HDPS', 0.0),
            ('STOP_PNST', 3.2),
            ('STOP_SHVJ', 5.1),
        ]},
        
        {'route_id': '75', 'stops': [
            ('STOP_HDPS', 0.0),
            ('STOP_KHRD', 2.8),
            ('STOP_VMNR', 5.5),
        ]},
        
        # Nigdi Routes (11-15)
        {'route_id': '11', 'stops': [
            ('STOP_NGDI', 0.0),
            ('STOP_PMPR', 2.5),
            ('STOP_CHWT', 4.2),
            ('STOP_PCMC', 5.8),
        ]},
        
        {'route_id': '12', 'stops': [
            ('STOP_NGDI', 0.0),
            ('STOP_AKRD', 1.8),
        ]},
        
        {'route_id': '13', 'stops': [
            ('STOP_NGDI', 0.0),
            ('STOP_CHWT', 2.5),
        ]},
        
        {'route_id': '14', 'stops': [
            ('STOP_NGDI', 0.0),
            ('STOP_SNGV', 3.2),
        ]},
        
        {'route_id': '15', 'stops': [
            ('STOP_NGDI', 0.0),
            ('STOP_PHGW', 1.5),
        ]},
        
        # Bhosari Routes (21-24)
        {'route_id': '21', 'stops': [
            ('STOP_BHSR', 0.0),
            ('STOP_PCMC', 2.8),
        ]},
        
        {'route_id': '22', 'stops': [
            ('STOP_BHSR', 0.0),
            ('STOP_PMPR', 3.5),
        ]},
        
        {'route_id': '23', 'stops': [
            ('STOP_BHSR', 0.0),
            ('STOP_KSRW', 1.8),
        ]},
        
        {'route_id': '24', 'stops': [
            ('STOP_BHSR', 0.0),
            ('STOP_CHKN', 4.5),
        ]},
        
        # Wakad Routes (61-65)
        {'route_id': '61', 'stops': [
            ('STOP_WKAD', 0.0),
            ('STOP_HNEW', 3.5),
        ]},
        
        {'route_id': '62', 'stops': [
            ('STOP_WKAD', 0.0),
            ('STOP_BNRR', 2.8),
        ]},
        
        {'route_id': '63', 'stops': [
            ('STOP_WKAD', 0.0),
            ('STOP_AUNDH', 3.2),
        ]},
        
        {'route_id': '64', 'stops': [
            ('STOP_WKAD', 0.0),
            ('STOP_PCMC', 4.5),
        ]},
        
        {'route_id': '65', 'stops': [
            ('STOP_WKAD', 0.0),
            ('STOP_PSDR', 2.1),
        ]},
    ]
    
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        for route in sample_routes:
            route_id = route['route_id']
            
            for seq, (stop_id, distance) in enumerate(route['stops'], start=1):
                insert_sql = text("""
                    INSERT INTO route_stops (route_id, stop_id, stop_sequence, distance_from_start_km)
                    VALUES (:route_id, :stop_id, :stop_sequence, :distance)
                    ON CONFLICT (route_id, stop_sequence) DO NOTHING
                """)
                
                conn.execute(insert_sql, {
                    'route_id': route_id,
                    'stop_id': stop_id,
                    'stop_sequence': seq,
                    'distance': distance
                })
            
            print(f"✓ Added {len(route['stops'])} stops for route {route_id}")
        
        conn.commit()
    
    print("\n✓ Sample data populated successfully")


def verify_data():
    """Verify the data was inserted correctly"""
    
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Count total route stops
        result = conn.execute(text("SELECT COUNT(*) FROM route_stops"))
        count = result.scalar()
        print(f"\nTotal route stops: {count}")
        
        # Show sample data
        result = conn.execute(text("""
            SELECT rs.route_id, r.route_name, rs.stop_id, s.stop_name, rs.stop_sequence, rs.distance_from_start_km
            FROM route_stops rs
            JOIN routes r ON rs.route_id = r.route_id
            JOIN stops s ON rs.stop_id = s.stop_id
            WHERE rs.route_id = '1'
            ORDER BY rs.stop_sequence
        """))
        
        print("\nRoute 1 (Swargate to Katraj) stops:")
        print("-" * 80)
        for row in result:
            print(f"  {row.stop_sequence}. {row.stop_name} ({row.stop_id}) - {row.distance_from_start_km}km")


def test_corridor_detection():
    """Test corridor detection with intermediate stops"""
    
    from app.drt.clustering import ClusteringService
    
    db = next(get_db())
    service = ClusteringService(db)
    
    print("\n" + "=" * 80)
    print("TESTING CORRIDOR DETECTION")
    print("=" * 80)
    
    # Test with intermediate stop (Market Yard)
    print("\nTest 1: Market Yard (intermediate stop on Route 1)")
    corridors = service._map_stop_to_corridors('STOP_MRKT')
    print(f"  Routes serving Market Yard: {corridors}")
    print(f"  Expected: Should include Route 1 (Swargate-Katraj)")
    
    # Test with end stop (Katraj)
    print("\nTest 2: Katraj (end stop of Route 1)")
    corridors = service._map_stop_to_corridors('STOP_KTRJ')
    print(f"  Routes serving Katraj: {corridors}")
    
    # Test with start stop (Swargate)
    print("\nTest 3: Swargate (start stop of multiple routes)")
    corridors = service._map_stop_to_corridors('STOP_SWGT')
    print(f"  Routes serving Swargate: {corridors}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("ROUTE STOPS TABLE SETUP")
    print("=" * 80)
    print()
    
    try:
        # Step 1: Create table
        print("Step 1: Creating route_stops table...")
        create_route_stops_table()
        print()
        
        # Step 2: Populate sample data
        print("Step 2: Populating sample data...")
        populate_sample_data()
        print()
        
        # Step 3: Verify data
        print("Step 3: Verifying data...")
        verify_data()
        print()
        
        # Step 4: Test corridor detection
        print("Step 4: Testing corridor detection...")
        test_corridor_detection()
        print()
        
        print("=" * 80)
        print("✓ SETUP COMPLETE!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Add more route stop sequences to route_stops table")
        print("2. Test pings at intermediate stops")
        print("3. Verify surge detection works along entire route corridor")
        print()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

