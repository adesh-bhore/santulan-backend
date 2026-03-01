"""Test Fast Optimizer Performance"""

import sys
from app.database.db import SessionLocal
from app.services.tsn_builder import TSNBuilder
from app.services.optimizer_fast import FastOptimizer
from app.models.base_models import Vehicle, Driver

def test_depot(depot_id: str, day_type: str = "weekday"):
    """Test optimization for a specific depot"""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*60}")
        print(f"Testing {depot_id} ({day_type})")
        print(f"{'='*60}")
        
        # Build TSN
        print("Building TSN...")
        builder = TSNBuilder(db)
        tsn = builder.build(depot_id=depot_id, day_type=day_type)
        
        trip_edges = [e for e in tsn.edges if e.edge_type == "trip"]
        print(f"TSN: {tsn.node_count} nodes, {tsn.edge_count} edges, {len(trip_edges)} trips")
        
        # Load resources
        vehicles = db.query(Vehicle).filter(Vehicle.depot_id == depot_id).all()
        drivers = db.query(Driver).filter(Driver.depot_id == depot_id).all()
        print(f"Resources: {len(vehicles)} vehicles, {len(drivers)} drivers")
        
        # Run optimization
        print("Running optimization...")
        optimizer = FastOptimizer()
        result = optimizer.optimize(
            tsn=tsn,
            vehicles=vehicles,
            drivers=drivers,
            time_limit_seconds=120
        )
        
        print(f"\n✅ {result.solver_status} in {result.solver_time_seconds:.2f}s")
        print(f"Fleet Size: {result.metrics.fleet_size} vehicles")
        print(f"Trips Covered: {result.metrics.trips_covered}/{result.metrics.trips_total}")
        print(f"Deadhead: {result.metrics.total_deadhead_km:.1f} km")
        print(f"Emissions: {result.metrics.estimated_emissions_kg:.1f} kg CO2")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Test all depots by size
    depots = [
        ("DEPOT_BHSR", "Small depot (156 trips)"),
        ("DEPOT_NGDI", "small depot (457 trips)"),
    ]
    
    for depot_id, description in depots:
        print(f"\n{description}")
        test_depot(depot_id, "weekday")
