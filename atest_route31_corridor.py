#!/usr/bin/env python3
"""
Test Route 31 Corridor Detection

Creates random pings across all stops on Route 31 corridor:
- 3 pings at Bibwewadi (STOP_BIBW)
- 4 pings at Dhankawadi (STOP_DHNK)
- 3 pings at Market Yard (STOP_MRKT)
- 5 pings at Swargate (STOP_SWGT)
- 4 pings at Katraj (STOP_KTRJ)

Total: 19 pings across 5 stops on Route 31

Expected:
- All stops should detect Route 31 in their corridor
- Clustering should group pings by Route 31 corridor
- Surge should show Route 31 in route_ids array
"""

from app.database.db import get_db
from app.drt.services import CommuterService
from app.drt.clustering import ClusteringService
from app.drt.models import Commuter, CommuterPing, SurgeEvent
from app.models.base_models import Stop
from sqlalchemy import text, func
import random

# Route 31 stops (Katraj → Bibwewadi → Dhankawadi → Market Yard → Swargate)
ROUTE_31_STOPS = [
    {
        "name": "Katraj",
        "stop_id": "STOP_KTRJ",
        "lat": 18.44870,
        "lng": 73.86240,
        "ping_count": 4
    },
    {
        "name": "Bibwewadi",
        "stop_id": "STOP_BIBW",
        "lat": 18.47412,
        "lng": 73.86890,
        "ping_count": 3
    },
    {
        "name": "Dhankawadi",
        "stop_id": "STOP_DHNK",
        "lat": 18.46712,
        "lng": 73.85261,
        "ping_count": 4
    },
    {
        "name": "Market Yard",
        "stop_id": "STOP_MRKT",
        "lat": 18.49816,
        "lng": 73.85514,
        "ping_count": 3
    },
    {
        "name": "Swargate",
        "stop_id": "STOP_SWGT",
        "lat": 18.50184,
        "lng": 73.86554,
        "ping_count": 5
    }
]


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)


def print_route_info():
    """Print Route 31 information"""
    print_header("ROUTE 31 CORRIDOR TEST")
    print("\nRoute 31: Katraj → Bibwewadi → Dhankawadi → Market Yard → Swargate")
    print("\nTest Plan:")
    print("  • 4 pings at Katraj (STOP_KTRJ)")
    print("  • 3 pings at Bibwewadi (STOP_BIBW)")
    print("  • 4 pings at Dhankawadi (STOP_DHNK)")
    print("  • 3 pings at Market Yard (STOP_MRKT)")
    print("  • 5 pings at Swargate (STOP_SWGT)")
    print("  • Total: 19 pings across 5 stops")
    print("\nExpected Results:")
    print("  ✓ All stops should detect Route 31 in corridor")
    print("  ✓ Clustering should group pings by Route 31")
    print("  ✓ Surge should show Route 31 in route_ids array")
    print()


def get_or_create_commuters(db, count):
    """Get or create test commuters"""
    
    print_header("STEP 1: Preparing Commuters")
    
    commuters = []
    
    print(f"\nCreating/finding {count} test commuters:")
    for i in range(1, count + 1):
        phone = f"900000{i:04d}"
        commuter = db.query(Commuter).filter(Commuter.phone == phone).first()
        
        if not commuter:
            commuter = CommuterService.register_commuter(
                db=db,
                phone=phone,
                name=f"Test Commuter {i}",
                password="test123"
            )
            print(f"  {i}. Created {phone} - {commuter.name}")
        else:
            print(f"  {i}. Found {phone} - {commuter.name}")
        
        commuters.append(commuter)
    
    print(f"\n✓ Total commuters ready: {len(commuters)}")
    return commuters


def create_pings_at_stop(db, stop_info, commuters, start_idx):
    """Create pings at a specific stop"""
    
    stop_name = stop_info['name']
    stop_id = stop_info['stop_id']
    lat = stop_info['lat']
    lng = stop_info['lng']
    ping_count = stop_info['ping_count']
    
    print(f"\n{stop_name} ({stop_id}):")
    print(f"  Location: {lat}, {lng}")
    print(f"  Creating {ping_count} pings...")
    
    pings = []
    
    for i in range(ping_count):
        commuter = commuters[start_idx + i]
        
        # Add random variation (±50 meters)
        lat_variation = random.uniform(-0.0005, 0.0005)
        lng_variation = random.uniform(-0.0005, 0.0005)
        
        ping_lat = lat + lat_variation
        ping_lng = lng + lng_variation
        
        ping, detected_stop = CommuterService.create_ping(
            db=db,
            commuter_id=commuter.commuter_id,
            latitude=ping_lat,
            longitude=ping_lng,
            ping_metadata={"test": "route31_corridor", "stop": stop_id}
        )
        
        pings.append(ping)
        
        stop_detected = detected_stop.stop_name if detected_stop else "None"
        print(f"    {i+1}. {commuter.phone} → Ping {ping.ping_id} → {stop_detected}")
    
    print(f"  ✓ Created {len(pings)} pings at {stop_name}")
    return pings


def create_all_pings(db, commuters):
    """Create pings at all Route 31 stops"""
    
    print_header("STEP 2: Creating Pings Across Route 31 Corridor")
    
    all_pings = []
    commuter_idx = 0
    
    for stop_info in ROUTE_31_STOPS:
        pings = create_pings_at_stop(db, stop_info, commuters, commuter_idx)
        all_pings.extend(pings)
        commuter_idx += stop_info['ping_count']
    
    print(f"\n✓ Total pings created: {len(all_pings)}")
    return all_pings


def verify_corridor_detection(db):
    """Verify that Route 31 is detected for all stops"""
    
    print_header("STEP 3: Verifying Corridor Detection")
    
    service = ClusteringService(db)
    
    print("\nChecking which routes serve each stop:")
    
    all_correct = True
    
    for stop_info in ROUTE_31_STOPS:
        stop_id = stop_info['stop_id']
        stop_name = stop_info['name']
        
        corridors = service._map_stop_to_corridors(stop_id)
        
        has_route_31 = '31' in corridors
        status = "✓" if has_route_31 else "✗"
        
        print(f"\n  {status} {stop_name} ({stop_id}):")
        print(f"      Routes: {corridors}")
        
        if has_route_31:
            print(f"      ✓ Route 31 detected!")
        else:
            print(f"      ✗ Route 31 NOT detected!")
            all_correct = False
    
    if all_correct:
        print("\n✅ All stops correctly detect Route 31!")
    else:
        print("\n⚠️ Some stops do not detect Route 31!")
        print("   Make sure route_stops table is populated with Route 31 data.")
    
    return all_correct


def verify_pings(db):
    """Verify all pings are pending"""
    
    print_header("STEP 4: Verifying Pending Pings")
    
    # Count pings by stop
    ping_counts = db.query(
        CommuterPing.detected_stop_id,
        Stop.stop_name,
        func.count(CommuterPing.ping_id).label('count')
    ).join(
        Stop, CommuterPing.detected_stop_id == Stop.stop_id
    ).filter(
        CommuterPing.status == 'pending'
    ).group_by(
        CommuterPing.detected_stop_id,
        Stop.stop_name
    ).all()
    
    print("\nPending Pings by Stop:")
    for stop_id, stop_name, count in ping_counts:
        print(f"  {stop_name} ({stop_id}): {count} pings")
    
    total_pending = db.query(CommuterPing).filter(
        CommuterPing.status == 'pending'
    ).count()
    
    print(f"\n✓ Total pending pings: {total_pending}")
    
    return total_pending


def run_clustering(db):
    """Run clustering job"""
    
    print_header("STEP 5: Running Clustering Job")
    
    print("\nRunning clustering...")
    service = ClusteringService(db)
    result = service.run_clustering_job()
    
    print(f"\nClustering Result:")
    print(f"  Status: {result['status']}")
    print(f"  Pending Pings Processed: {result.get('pending_pings', 0)}")
    print(f"  Surges Detected: {result.get('surges_detected', 0)}")
    
    if result['status'] == 'error':
        print(f"  Error: {result.get('error', 'Unknown error')}")
    
    return result


def verify_surges(db):
    """Verify surge events created with Route 31"""
    
    print_header("STEP 6: Verifying Surge Events")
    
    surges = db.query(SurgeEvent, Stop).join(
        Stop, SurgeEvent.stop_id == Stop.stop_id
    ).filter(
        SurgeEvent.status == 'pending'
    ).order_by(SurgeEvent.detected_at.desc()).all()
    
    if not surges:
        print("\n❌ No surge events found!")
        print("   Note: Surge threshold is 10 pings (demo mode)")
        print("   Individual stops have fewer pings, so no surges expected.")
        return False
    
    print(f"\nFound {len(surges)} surge event(s):")
    
    route_31_detected = False
    
    for surge, stop in surges:
        print(f"\n  Surge ID: {surge.surge_id}")
        print(f"  Stop: {stop.stop_name} ({surge.stop_id})")
        print(f"  Route IDs: {surge.route_ids}")
        print(f"  Ping Count: {surge.ping_count}")
        print(f"  Status: {surge.status}")
        print(f"  Detected At: {surge.detected_at}")
        
        if '31' in surge.route_ids:
            print(f"  ✓ Route 31 detected in surge!")
            route_31_detected = True
        else:
            print(f"  ⚠️ Route 31 NOT in surge route_ids")
    
    if route_31_detected:
        print(f"\n✅ Route 31 detected in surge events!")
    else:
        print(f"\n⚠️ Route 31 not detected in any surge")
    
    return route_31_detected


def show_surge_summary(db):
    """Show detailed surge summary"""
    
    print_header("SURGE SUMMARY")
    
    result = db.execute(text("""
        SELECT 
            se.surge_id,
            se.stop_id,
            s.stop_name,
            se.route_ids,
            se.ping_count,
            se.status,
            se.detected_at,
            COUNT(cp.ping_id) as actual_pings
        FROM surge_events se
        JOIN stops s ON se.stop_id = s.stop_id
        LEFT JOIN commuter_pings cp ON cp.surge_event_id = se.surge_id
        WHERE se.status = 'pending'
        GROUP BY se.surge_id, se.stop_id, s.stop_name, se.route_ids, se.ping_count, se.status, se.detected_at
        ORDER BY se.detected_at DESC
    """))
    
    surges = result.fetchall()
    
    if not surges:
        print("\nNo active surge events found.")
        print("\nNote: With DRT_SURGE_PING_THRESHOLD=10 (demo mode):")
        print("  • Individual stops have 3-5 pings each")
        print("  • Not enough to trigger surge at individual stops")
        print("  • To test surge creation, either:")
        print("    1. Lower threshold: DRT_SURGE_PING_THRESHOLD=3")
        print("    2. Create more pings at one stop")
        return
    
    print("\n┌─────────────────────────────────────────────────────────────────────────────┐")
    print("│                           ACTIVE SURGE EVENTS                               │")
    print("├─────────────────────────────────────────────────────────────────────────────┤")
    
    for surge in surges:
        surge_id, stop_id, stop_name, route_ids, ping_count, status, detected_at, actual_pings = surge
        
        print(f"│ Surge #{surge_id:<3} │ {stop_name:<20} │ Routes: {str(route_ids):<15} │")
        print(f"│           │ Pings: {ping_count:<3} (actual: {actual_pings:<3})                              │")
        print("├─────────────────────────────────────────────────────────────────────────────┤")
    
    print("└─────────────────────────────────────────────────────────────────────────────┘")


def show_ping_distribution(db):
    """Show ping distribution across Route 31 stops"""
    
    print_header("PING DISTRIBUTION")
    
    result = db.execute(text("""
        SELECT 
            s.stop_name,
            cp.detected_stop_id,
            COUNT(cp.ping_id) as ping_count,
            cp.status
        FROM commuter_pings cp
        JOIN stops s ON cp.detected_stop_id = s.stop_id
        WHERE cp.detected_stop_id IN ('STOP_KTRJ', 'STOP_BIBW', 'STOP_DHNK', 'STOP_MRKT', 'STOP_SWGT')
        GROUP BY s.stop_name, cp.detected_stop_id, cp.status
        ORDER BY 
            CASE cp.detected_stop_id
                WHEN 'STOP_KTRJ' THEN 1
                WHEN 'STOP_BIBW' THEN 2
                WHEN 'STOP_DHNK' THEN 3
                WHEN 'STOP_MRKT' THEN 4
                WHEN 'STOP_SWGT' THEN 5
            END
    """))
    
    pings = result.fetchall()
    
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│              Route 31 Corridor Ping Distribution            │")
    print("├─────────────────────────────────────────────────────────────┤")
    
    for stop_name, stop_id, ping_count, status in pings:
        print(f"│ {stop_name:<20} │ {stop_id:<12} │ {ping_count:>3} pings │ {status:<10} │")
    
    print("└─────────────────────────────────────────────────────────────┘")


def cleanup_test_data(db):
    """Cleanup test data"""
    
    print_header("CLEANUP")
    
    response = input("\nCleanup test data? (y/n): ")
    
    if response.lower() == 'y':
        # Delete test pings
        deleted_pings = db.execute(text("""
            DELETE FROM commuter_pings 
            WHERE commuter_id IN (
                SELECT commuter_id FROM commuters WHERE phone LIKE '900000%'
            )
        """)).rowcount
        
        # Delete test surges
        deleted_surges = db.execute(text("""
            DELETE FROM surge_events WHERE status = 'pending'
        """)).rowcount
        
        # Delete test commuters
        deleted_commuters = db.execute(text("""
            DELETE FROM commuters WHERE phone LIKE '900000%'
        """)).rowcount
        
        db.commit()
        
        print(f"\n✓ Deleted {deleted_pings} test pings")
        print(f"✓ Deleted {deleted_surges} test surges")
        print(f"✓ Deleted {deleted_commuters} test commuters")
    else:
        print("\n✓ Test data kept for manual inspection")


def main():
    """Main test function"""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 22 + "ROUTE 31 CORRIDOR TEST" + " " * 34 + "║")
    print("╚" + "=" * 78 + "╝")
    
    print_route_info()
    
    input("Press Enter to start...")
    
    try:
        db = next(get_db())
        
        # Calculate total commuters needed
        total_pings = sum(stop['ping_count'] for stop in ROUTE_31_STOPS)
        
        # Step 1: Get/create commuters
        commuters = get_or_create_commuters(db, total_pings)
        
        # Step 2: Create pings across all Route 31 stops
        all_pings = create_all_pings(db, commuters)
        
        # Step 3: Verify corridor detection
        corridor_ok = verify_corridor_detection(db)
        
        # Step 4: Verify pings
        total_pending = verify_pings(db)
        
        # Step 5: Show ping distribution
        show_ping_distribution(db)
        
        # Step 6: Run clustering
        result = run_clustering(db)
        
        # Step 7: Verify surges
        surge_ok = verify_surges(db)
        
        # Step 8: Show summary
        show_surge_summary(db)
        
        # Final result
        print_header("TEST RESULT")
        
        if corridor_ok:
            print("\n✅ CORRIDOR DETECTION: PASSED")
            print("   All stops correctly detect Route 31")
        else:
            print("\n❌ CORRIDOR DETECTION: FAILED")
            print("   Some stops do not detect Route 31")
        
        if total_pending == total_pings:
            print("\n✅ PING CREATION: PASSED")
            print(f"   All {total_pings} pings created successfully")
        else:
            print("\n⚠️ PING CREATION: PARTIAL")
            print(f"   Expected {total_pings}, found {total_pending}")
        
        print("\n" + "=" * 80)
        print("\nNOTE: Surge threshold is 10 pings (demo mode)")
        print("Individual stops have 3-5 pings each, so no surges expected.")
        print("To test surge creation:")
        print("  1. Lower threshold: DRT_SURGE_PING_THRESHOLD=3")
        print("  2. Or create more pings at one stop")
        print("=" * 80)
        
        # Cleanup option
        cleanup_test_data(db)
        
        print("\n✓ Test complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
