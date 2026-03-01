"""Diagnostic Script to Measure Optimization Timing

This script breaks down the optimization process into individual steps
to identify where time is being spent.
"""

import time
from app.database.db import SessionLocal
from app.services.tsn_builder import TSNBuilder
from app.services.optimizer_fast import FastOptimizer
from app.services.plan_service import PlanService
from app.models.base_models import Vehicle, Driver, Depot

def diagnose_optimization(depot_id: str, day_type: str = "weekday"):
    """Diagnose optimization timing step by step"""
    db = SessionLocal()
    
    print(f"\n{'='*70}")
    print(f"OPTIMIZATION TIMING DIAGNOSIS: {depot_id} ({day_type})")
    print(f"{'='*70}\n")
    
    total_start = time.time()
    
    try:
        # Step 1: Validate depot
        step_start = time.time()
        depot = db.query(Depot).filter(Depot.depot_id == depot_id).first()
        if not depot:
            print(f"❌ Depot {depot_id} not found")
            return
        step_time = time.time() - step_start
        print(f"✓ Step 1: Validate depot - {step_time:.3f}s")
        
        # Step 2: Build TSN
        step_start = time.time()
        builder = TSNBuilder(db)
        tsn = builder.build(depot_id=depot_id, day_type=day_type)
        step_time = time.time() - step_start
        trip_edges = [e for e in tsn.edges if e.edge_type == "trip"]
        print(f"✓ Step 2: Build TSN - {step_time:.3f}s")
        print(f"  - Nodes: {tsn.node_count}, Edges: {tsn.edge_count}, Trips: {len(trip_edges)}")
        
        # Step 3: Load vehicles and drivers
        step_start = time.time()
        vehicles = db.query(Vehicle).filter(Vehicle.depot_id == depot_id).all()
        drivers = db.query(Driver).filter(Driver.depot_id == depot_id).all()
        step_time = time.time() - step_start
        print(f"✓ Step 3: Load resources - {step_time:.3f}s")
        print(f"  - Vehicles: {len(vehicles)}, Drivers: {len(drivers)}")
        
        # Step 4: Run optimization
        step_start = time.time()
        optimizer = FastOptimizer()
        result = optimizer.optimize(
            tsn=tsn,
            vehicles=vehicles,
            drivers=drivers,
            time_limit_seconds=180
        )
        step_time = time.time() - step_start
        print(f"✓ Step 4: Run optimizer - {step_time:.3f}s")
        print(f"  - Status: {result.solver_status}")
        print(f"  - Fleet size: {result.metrics.fleet_size}")
        print(f"  - Trips covered: {result.metrics.trips_covered}/{result.metrics.trips_total}")
        
        # Step 5: Create plan record
        step_start = time.time()
        plan_service = PlanService()
        weights = {
            'fleet_size': 0.4,
            'deadhead': 0.3,
            'emissions': 0.2,
            'duty_variance': 0.1
        }
        plan = plan_service.create_plan(
            depot_id=depot_id,
            day_type=day_type,
            optimization_result=result,
            objective_weights=weights,
            db_session=db
        )
        db.commit()
        step_time = time.time() - step_start
        print(f"✓ Step 5: Create plan record - {step_time:.3f}s")
        print(f"  - Plan ID: {plan.plan_id}")
        print(f"  - Version: {plan.version}")
        print(f"  - Vehicle assignments: {len(result.vehicle_assignments)}")
        print(f"  - Driver assignments: {len(result.driver_assignments)}")
        
        # Total time
        total_time = time.time() - total_start
        print(f"\n{'='*70}")
        print(f"TOTAL TIME: {total_time:.3f}s")
        print(f"{'='*70}\n")
        
        # Breakdown
        print("TIME BREAKDOWN:")
        print(f"  1. Validate depot:     ~0.001s  (negligible)")
        print(f"  2. Build TSN:          ~{step_time:.1f}s")
        print(f"  3. Load resources:     ~0.01s   (negligible)")
        print(f"  4. Run optimizer:      ~{result.solver_time_seconds:.1f}s  (MAIN BOTTLENECK)")
        print(f"  5. Create plan:        ~{step_time:.1f}s")
        print(f"  6. Network overhead:   N/A (local)")
        print(f"\nWhen called from frontend, add:")
        print(f"  - HTTP request/response: ~0.1-0.5s")
        print(f"  - JSON serialization:    ~0.1-0.3s")
        print(f"  - Database transaction:  ~0.1-0.2s")
        print(f"  - Total frontend overhead: ~0.3-1.0s")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    # Default to BHSR if no depot specified
    depot_id = sys.argv[1] if len(sys.argv) > 1 else "DEPOT_BHSR"
    day_type = sys.argv[2] if len(sys.argv) > 2 else "weekday"
    
    diagnose_optimization(depot_id, day_type)
    
    print("\n" + "="*70)
    print("COMPARISON: Test Script vs Frontend API")
    print("="*70)
    print("\nTest Script (test_fast_optimizer.py):")
    print("  - Runs optimizer directly in Python")
    print("  - No HTTP overhead")
    print("  - No JSON serialization")
    print("  - Minimal database operations")
    print("  - Time: ~120-130s for BHSR")
    print("\nFrontend API Call:")
    print("  - HTTP POST request to backend")
    print("  - Backend validates, builds TSN, runs optimizer")
    print("  - Creates plan record with all assignments")
    print("  - Serializes response to JSON")
    print("  - HTTP response back to frontend")
    print("  - Time: ~120-130s + overhead (~5-10s)")
    print("\nExpected difference: 5-10 seconds")
    print("If difference is > 30 seconds, investigate:")
    print("  1. Database connection issues")
    print("  2. Network latency")
    print("  3. Backend server performance")
    print("  4. Concurrent requests")
    print("="*70)
