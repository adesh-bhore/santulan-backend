#!/usr/bin/env python3
"""
Test Multi-Corridor Clustering

Creates pings across TWO independent route corridors:

Route 31 Corridor (Katraj → Swargate):
- 4 pings at Katraj
- 3 pings at Bibwewadi
- 4 pings at Dhankawadi
- 3 pings at Market Yard
- 5 pings at Swargate
Total: 19 pings

Route 72 Corridor (Hadapsar → Swargate):
- 8 pings at Hadapsar
- 4 pings at Fatima Nagar
- 3 pings at Wanowrie
Total: 15 pings

Grand Total: 34 pings across 8 stops on 2 corridors

Expected:
- Corridor 1: Surge for Route 31 (19 pings >= 10)
- Corridor 2: Surge for Route 72 (15 pings >= 10)
- Total: 2 independent surges
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
        "ping_count": 4,
        "route": "Route 31"
    },
    {
        "name": "Bibwewadi",
        "stop_id": "STOP_BIBW",
        "lat": 18.47412,
        "lng": 73.86890,
        "ping_count": 3,
        "route": "Route 31"
    },
    {
        "name": "Dhankawadi",
        "stop_id": "STOP_DHNK",
        "lat": 18.46712,
        "lng": 73.85261,
        "ping_count": 4,
        "route": "Route 31"
    },
    {
        "name": "Market Yard",
        "stop_id": "STOP_MRKT",
        "lat": 18.49816,
        "lng": 73.85514,
        "ping_count": 3,
        "route": "Route 31"
    },
    {
        "name": "Swargate",
        "stop_id": "STOP_SWGT",
        "lat": 18.50184,
        "lng": 73.86554,
        "ping_count": 5,
        "route": "Route 31"
    }
]

# Route 72 stops (Hadapsar → Fatima Nagar → Wanowrie → Swargate)
ROUTE_72_STOPS = [
    {
        "name": "Hadapsar",
        "stop_id": "STOP_HDPS",
        "lat": 18.50851,
        "lng": 73.93692,
        "ping_count": 8,
        "route": "Route 72"
    },
    {
        "name": "Fatima Nagar",
        "stop_id": "STOP_FTHS",
        "lat": 18.52124,
        "lng": 73.88654,
        "ping_count": 4,
        "route": "Route 72"
    },
    {
        "name": "Wanowrie",
        "stop_id": "STOP_WNGV",
        "lat": 18.49582,
        "lng": 73.88967,
        "ping_count": 3,
        "route": "Route 72"
    }
]


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)


def print_route_info():
    """Print test information"""
    print_header("MULTI-CORRIDOR CLUSTERING TEST")
    print("\nRoute 31 Corridor: Katraj → Bibwewadi → Dhankawadi → Market Yard → Swargate")
    print("Route 72 Corridor: Hadapsar → Fatima Nagar → Wanowrie → Swargate")
    print("\nTest Plan:")
    print("\n  Route 31 Corridor:")
    print("    • 4 pings at Katraj (STOP_KTRJ)")
    print("    • 3 pings at Bibwewadi (STOP_BIBW)")
    print("    • 4 pings at Dhankawadi (STOP_DHNK)")
    print("    • 3 pings at Market Yard (STOP_MRKT)")
    print("    • 5 pings at Swargate (STOP_SWGT)")
    print("    • Subtotal: 19 pings")
    print("\n  Route 72 Corridor:")
    print("    • 8 pings at Hadapsar (STOP_HDPS)")
    print("    • 4 pings at Fatima Nagar (STOP_FTHS)")
    print("    • 3 pings at Wanowrie (STOP_WNGV)")
    print("    • Subtotal: 15 pings")
    print("\n  Grand Total: 34 pings across 8 stops on 2 corridors")
    print("\nExpected Results:")
    print("  ✓ Surge 1: Route 31 corridor (19 pings >= 10)")
    print("  ✓ Surge 2: Route 72 corridor (15 pings >= 10)")
    print("  ✓ Total: 2 independent surges")
    print("  ✓ No duplicate surges")
    print()
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


def create_pings_for_corridor(db, corridor_stops, commuters, start_idx, corridor_name):
    """Create pings for a specific corridor"""
    
    print_header(f"Creating Pings for {corridor_name}")
    
    all_pings = []
    commuter_idx = start_idx
    
    for stop_info in corridor_stops:
        pings = create_pings_at_stop(db, stop_info, commuters, commuter_idx)
        all_pings.extend(pings)
        commuter_idx += stop_info['ping_count']
    
    print(f"\n✓ Total pings created for {corridor_name}: {len(all_pings)}")
    return all_pings, commuter_idx


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
    """Verify that routes are detected for all stops"""
    
    print_header("STEP 3: Verifying Corridor Detection")
    
    service = ClusteringService(db)
    
    print("\nRoute 31 Corridor:")
    route31_ok = True
    for stop_info in ROUTE_31_STOPS:
        stop_id = stop_info['stop_id']
        stop_name = stop_info['name']
        
        corridors = service._map_stop_to_corridors(stop_id)
        
        has_route_31 = '31' in corridors or '1' in corridors
        status = "✓" if has_route_31 else "✗"
        
        print(f"  {status} {stop_name} ({stop_id}): {corridors}")
        
        if not has_route_31:
            route31_ok = False
    
    print("\nRoute 72 Corridor:")
    route72_ok = True
    for stop_info in ROUTE_72_STOPS:
        stop_id = stop_info['stop_id']
        stop_name = stop_info['name']
        
        corridors = service._map_stop_to_corridors(stop_id)
        
        has_route_72 = '72' in corridors or '3' in corridors
        status = "✓" if has_route_72 else "✗"
        
        print(f"  {status} {stop_name} ({stop_id}): {corridors}")
        
        if not has_route_72:
            route72_ok = False
    
    if route31_ok and route72_ok:
        print("\n✅ All stops correctly detect their routes!")
    else:
        print("\n⚠️ Some stops do not detect expected routes!")
    
    return route31_ok and route72_ok


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
    """Verify surge events created for both corridors"""
    
    print_header("STEP 6: Verifying Surge Events")
    
    surges = db.query(SurgeEvent, Stop).join(
        Stop, SurgeEvent.stop_id == Stop.stop_id
    ).filter(
        SurgeEvent.status == 'pending'
    ).order_by(SurgeEvent.detected_at.desc()).all()
    
    if not surges:
        print("\n❌ No surge events found!")
        print("   Note: Surge threshold is 10 pings (demo mode)")
        print("   Expected: 2 surges (Route 31: 19 pings, Route 72: 15 pings)")
        return False
    
    print(f"\nFound {len(surges)} surge event(s):")
    
    route_31_detected = False
    route_72_detected = False
    
    for surge, stop in surges:
        print(f"\n  Surge ID: {surge.surge_id}")
        print(f"  Stop: {stop.stop_name} ({surge.stop_id})")
        print(f"  Route IDs: {surge.route_ids}")
        print(f"  Ping Count: {surge.ping_count}")
        print(f"  Status: {surge.status}")
        print(f"  Detected At: {surge.detected_at}")
        
        # Check for Route 31 or Route 1 (both serve same corridor)
        if '31' in surge.route_ids or '1' in surge.route_ids:
            print(f"  ✓ Route 31 corridor detected!")
            route_31_detected = True
        
        # Check for Route 72 or Route 3 (both serve Hadapsar)
        if '72' in surge.route_ids or '3' in surge.route_ids:
            print(f"  ✓ Route 72 corridor detected!")
            route_72_detected = True
    
    print("\n" + "=" * 80)
    if route_31_detected and route_72_detected:
        print("✅ Both corridor surges detected successfully!")
    elif route_31_detected:
        print("⚠️ Only Route 31 corridor surge detected")
    elif route_72_detected:
        print("⚠️ Only Route 72 corridor surge detected")
    else:
        print("❌ No corridor surges detected")
    
    return route_31_detected and route_72_detected


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
    print("║" + " " * 20 + "MULTI-CORRIDOR CLUSTERING TEST" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    
    print_route_info()
    
    try:
        db = next(get_db())
        
        # STEP 0: CLEANUP OLD DATA FIRST
        print_header("STEP 0: Cleaning Up Old Test Data")
        
        # Delete old test pings
        deleted_pings = db.execute(text("""
            DELETE FROM commuter_pings 
            WHERE commuter_id IN (
                SELECT commuter_id FROM commuters WHERE phone LIKE '900000%'
            )
        """)).rowcount
        
        # Delete ALL pending surges (to avoid conflicts)
        deleted_surges = db.execute(text("""
            DELETE FROM surge_events WHERE status = 'pending'
        """)).rowcount
        
        # Delete old test commuters
        deleted_commuters = db.execute(text("""
            DELETE FROM commuters WHERE phone LIKE '900000%'
        """)).rowcount
        
        db.commit()
        
        print(f"\n✓ Cleaned up {deleted_pings} old pings")
        print(f"✓ Cleaned up {deleted_surges} old pending surges")
        print(f"✓ Cleaned up {deleted_commuters} old commuters")
        print("\n✓ Database ready for fresh test\n")
        
        input("Press Enter to continue...")
        
        # Calculate total commuters needed
        total_route31 = sum(stop['ping_count'] for stop in ROUTE_31_STOPS)
        total_route72 = sum(stop['ping_count'] for stop in ROUTE_72_STOPS)
        total_pings = total_route31 + total_route72
        
        # Step 1: Get/create commuters
        commuters = get_or_create_commuters(db, total_pings)
        
        # Step 2: Create pings for Route 31 corridor
        route31_pings, next_idx = create_pings_for_corridor(
            db, ROUTE_31_STOPS, commuters, 0, "Route 31 Corridor"
        )
        
        # Step 3: Create pings for Route 72 corridor
        route72_pings, _ = create_pings_for_corridor(
            db, ROUTE_72_STOPS, commuters, next_idx, "Route 72 Corridor"
        )
        
        all_pings = route31_pings + route72_pings
        
        # Step 4: Verify corridor detection
        corridor_ok = verify_corridor_detection(db)
        
        # Step 5: Verify pings
        total_pending = verify_pings(db)
        
        # Step 6: Show ping distribution
        show_ping_distribution(db)
        
        # Step 7: Run clustering
        result = run_clustering(db)
        
        # Step 8: Verify surges
        surge_ok = verify_surges(db)
        
        # Step 9: Show summary
        show_surge_summary(db)
        
        # Final result
        print_header("TEST RESULT")
        
        if corridor_ok:
            print("\n✅ CORRIDOR DETECTION: PASSED")
            print("   All stops correctly detect their routes")
        else:
            print("\n❌ CORRIDOR DETECTION: FAILED")
            print("   Some stops do not detect expected routes")
        
        if total_pending == total_pings:
            print("\n✅ PING CREATION: PASSED")
            print(f"   All {total_pings} pings created successfully")
        else:
            print("\n⚠️ PING CREATION: PARTIAL")
            print(f"   Expected {total_pings}, found {total_pending}")
        
        if surge_ok:
            print("\n✅ SURGE DETECTION: PASSED")
            print("   Both corridor surges detected")
        else:
            print("\n⚠️ SURGE DETECTION: PARTIAL")
            print("   Not all corridor surges detected")
        
        print("\n" + "=" * 80)
        print("\nExpected with Threshold=10:")
        print("  ✓ Surge 1: Route 31 corridor (19 pings)")
        print("  ✓ Surge 2: Route 72 corridor (15 pings)")
        print("  ✓ Total: 2 independent surges")
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
