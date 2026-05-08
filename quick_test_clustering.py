#!/usr/bin/env python3
"""
Quick Corridor Clustering Test

Simple script to quickly test corridor clustering:
- 10 pings at Market Yard (should create surge for Route 1)
- 6 pings at Pune Station (should NOT create surge)
"""

from app.database.db import get_db
from app.drt.services import CommuterService
from app.drt.clustering import ClusteringService

# Test coordinates
MARKET_YARD = {"lat": 18.49816, "lng": 73.85514, "name": "Market Yard"}
PUNE_STATION = {"lat": 18.52859, "lng": 73.87420, "name": "Pune Station"}

def quick_test():
    db = next(get_db())
    
    print("\n" + "=" * 60)
    print("QUICK CORRIDOR CLUSTERING TEST")
    print("=" * 60)
    
    # Get or create test commuter
    from app.drt.models import Commuter
    commuter = db.query(Commuter).filter(Commuter.phone == "9999999999").first()
    if not commuter:
        commuter = CommuterService.register_commuter(
            db=db, phone="9999999999", name="Quick Test User", password="test123"
        )
    
    print(f"\nUsing commuter: {commuter.commuter_id}")
    
    # Create 10 pings at Market Yard
    print(f"\n1. Creating 10 pings at {MARKET_YARD['name']}...")
    for i in range(10):
        ping, stop = CommuterService.create_ping(
            db=db,
            commuter_id=commuter.commuter_id,
            latitude=MARKET_YARD['lat'] + (i * 0.0001),
            longitude=MARKET_YARD['lng'] + (i * 0.0001)
        )
        print(f"   Ping {i+1}: {ping.ping_id} → {stop.stop_name if stop else 'None'}")
    
    # Create 6 pings at Pune Station
    print(f"\n2. Creating 6 pings at {PUNE_STATION['name']}...")
    for i in range(6):
        ping, stop = CommuterService.create_ping(
            db=db,
            commuter_id=commuter.commuter_id,
            latitude=PUNE_STATION['lat'] + (i * 0.0001),
            longitude=PUNE_STATION['lng'] + (i * 0.0001)
        )
        print(f"   Ping {i+1}: {ping.ping_id} → {stop.stop_name if stop else 'None'}")
    
    # Run clustering
    print(f"\n3. Running clustering job...")
    service = ClusteringService(db)
    result = service.run_clustering_job()
    
    print(f"\n   Status: {result['status']}")
    print(f"   Surges: {result.get('surges_detected', 0)}")
    
    # Check surges
    from app.drt.models import SurgeEvent
    surges = db.query(SurgeEvent).filter(SurgeEvent.status == 'pending').all()
    
    print(f"\n4. Surge Events:")
    if surges:
        for surge in surges:
            print(f"   - Stop: {surge.stop_id}, Routes: {surge.route_ids}, Count: {surge.ping_count}")
            if surge.stop_id == 'STOP_MRKT' and '1' in surge.route_ids:
                print(f"     ✅ SUCCESS! Route 1 detected at Market Yard!")
    else:
        print(f"   ❌ No surges created")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    quick_test()

