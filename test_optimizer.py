"""Test Optimizer Service

Tests the OR-Tools optimizer with TSN from database.
"""

import sys
sys.path.insert(0, '.')

from app.database.db import SessionLocal
from app.services.tsn_builder import TSNBuilder
from app.services.optimizer import Optimizer
from app.models.base_models import Vehicle, Driver

def test_optimizer():
    """Test optimizer with real data from smallest depot"""
    db = SessionLocal()
    
    try:
        # Use smallest depot for faster testing
        depot_id = "DEPOT_BHSR"
        day_type = "weekday"
        
        print(f"Testing Optimizer for {depot_id}")
        print("=" * 70)
        
        # Step 1: Build TSN
        print(f"\n1. Building TSN...")
        builder = TSNBuilder(db)
        tsn = builder.build(depot_id, day_type=day_type)
        print(f"   ✓ TSN built: {tsn.node_count} nodes, {tsn.edge_count} edges")
        
        # Step 2: Load vehicles and drivers
        print(f"\n2. Loading vehicles and drivers...")
        vehicles = db.query(Vehicle).filter(Vehicle.depot_id == depot_id).all()
        drivers = db.query(Driver).filter(Driver.depot_id == depot_id).all()
        print(f"   ✓ Loaded: {len(vehicles)} vehicles, {len(drivers)} drivers")
        
        # Step 3: Run optimization
        print(f"\n3. Running optimization...")
        optimizer = Optimizer()
        
        # Use custom weights
        objective_weights = {
            'fleet_size': 100.0,    # Minimize number of vehicles
            'deadhead': 10.0,       # Minimize empty movements
            'emissions': 5.0,       # Minimize emissions
            'duty_variance': 1.0    # Balance driver workload
        }
        
        result = optimizer.optimize(
            tsn=tsn,
            vehicles=vehicles,
            drivers=drivers,
            objective_weights=objective_weights,
            time_limit_seconds=30  # Short time limit for testing
        )
        
        # Step 4: Display results
        print(f"\n4. Optimization Results")
        print("   " + "-" * 66)
        print(f"   Status: {result.solver_status}")
        print(f"   Solve Time: {result.solver_time_seconds:.2f} seconds")
        print(f"\n   Metrics:")
        print(f"     Fleet Size: {result.metrics.fleet_size} vehicles")
        print(f"     Trips Covered: {result.metrics.trips_covered}/{result.metrics.trips_total}")
        print(f"     Total Deadhead: {result.metrics.total_deadhead_km:.2f} km")
        print(f"     Estimated Emissions: {result.metrics.estimated_emissions_kg:.2f} kg CO2")
        print(f"     Duty Variance: {result.metrics.duty_variance_minutes:.2f} minutes")
        
        # Detailed vehicle assignments
        print(f"\n   Vehicle Assignments (showing all {len(result.vehicle_assignments)} vehicles):")
        print("   " + "-" * 66)
        for vehicle_id in sorted(result.vehicle_assignments.keys()):
            trips = result.vehicle_assignments[vehicle_id]
            print(f"     {vehicle_id}: {len(trips)} trips")
            # Show first 3 trips for each vehicle
            for trip_id in trips[:3]:
                print(f"       - {trip_id}")
            if len(trips) > 3:
                print(f"       ... and {len(trips) - 3} more trips")
        
        # Detailed driver assignments
        print(f"\n   Driver Assignments (showing all {len(result.driver_assignments)} drivers):")
        print("   " + "-" * 66)
        for driver_id in sorted(result.driver_assignments.keys()):
            trips = result.driver_assignments[driver_id]
            print(f"     {driver_id}: {len(trips)} trips")
            # Show first 3 trips for each driver
            for trip_id in trips[:3]:
                print(f"       - {trip_id}")
            if len(trips) > 3:
                print(f"       ... and {len(trips) - 3} more trips")
        
        # Distribution analysis
        print(f"\n   Distribution Analysis:")
        print("   " + "-" * 66)
        vehicle_trip_counts = [len(trips) for trips in result.vehicle_assignments.values()]
        driver_trip_counts = [len(trips) for trips in result.driver_assignments.values()]
        
        print(f"     Vehicle trips: min={min(vehicle_trip_counts)}, "
              f"max={max(vehicle_trip_counts)}, "
              f"avg={sum(vehicle_trip_counts)/len(vehicle_trip_counts):.1f}")
        print(f"     Driver trips: min={min(driver_trip_counts)}, "
              f"max={max(driver_trip_counts)}, "
              f"avg={sum(driver_trip_counts)/len(driver_trip_counts):.1f}")
        
        print(f"\n{'=' * 70}")
        print("✓ Optimizer test complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_optimizer()
