"""Optimization API Routes

Handles optimization requests for vehicle and driver scheduling.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database.db import get_db
from app.services.tsn_builder import TSNBuilder
from app.services.optimizer_fast import FastOptimizer
from app.services.plan_service import PlanService
from app.models.base_models import Vehicle, Driver, Depot
from app.schemas.request_schemas import OptimizationRequest
from app.schemas.response_schemas import OptimizationResponse

router = APIRouter()


@router.post("/optimize", response_model=OptimizationResponse)
def run_optimization(
    request: OptimizationRequest,
    db: Session = Depends(get_db)
):
    """
    Run optimization for a specific depot.
    
    Process:
    1. Validate depot exists
    2. Build Time-Space Network (TSN)
    3. Load vehicles and drivers
    4. Run OR-Tools optimizer
    5. Return results with metrics
    """
    try:
        # Step 1: Validate depot
        depot = db.query(Depot).filter(Depot.depot_id == request.depot_id).first()
        if not depot:
            raise HTTPException(status_code=404, detail=f"Depot {request.depot_id} not found")
        
        # Step 2: Build TSN
        print(f"Building TSN for {request.depot_id}...")
        builder = TSNBuilder(db)
        tsn = builder.build(
            depot_id=request.depot_id,
            day_type=request.day_type
        )
        
        # Check if we have trips
        trip_edges = [e for e in tsn.edges if e.edge_type == "trip"]
        if not trip_edges:
            raise HTTPException(
                status_code=400,
                detail=f"No trips found for depot {request.depot_id} on {request.day_type}"
            )
        
        print(f"TSN built: {tsn.node_count} nodes, {tsn.edge_count} edges, {len(trip_edges)} trips")
        
        # Step 3: Load vehicles and drivers
        vehicles = db.query(Vehicle).filter(Vehicle.depot_id == request.depot_id).all()
        drivers = db.query(Driver).filter(Driver.depot_id == request.depot_id).all()
        
        if not vehicles:
            raise HTTPException(
                status_code=400,
                detail=f"No vehicles found for depot {request.depot_id}"
            )
        
        if not drivers:
            raise HTTPException(
                status_code=400,
                detail=f"No drivers found for depot {request.depot_id}"
            )
        
        print(f"Loaded: {len(vehicles)} vehicles, {len(drivers)} drivers")
        
        # Step 4: Run optimization
        print(f"Running optimization...")
        optimizer = FastOptimizer()
        
        # Use weights from request or defaults
        objective_weights = None
        if request.objective_weights:
            objective_weights = {
                'fleet_size': request.objective_weights.fleet_size,
                'deadhead': request.objective_weights.deadhead,
                'emissions': request.objective_weights.emissions,
                'duty_variance': request.objective_weights.duty_variance
            }
        
        result = optimizer.optimize(
            tsn=tsn,
            vehicles=vehicles,
            drivers=drivers,
            objective_weights=objective_weights,
            time_limit_seconds=300  # 5 minutes max (same as optimizer default)
        )
        
        print(f"Optimization complete: {result.solver_status} in {result.solver_time_seconds:.2f}s")
        print(f"✅ Optimization Metrics:")
        print(f"   Fleet Size: {result.metrics.fleet_size} vehicles")
        print(f"   Drivers Used: {result.metrics.drivers_used} drivers")
        print(f"   Trips Covered: {result.metrics.trips_covered}/{result.metrics.trips_total}")
        print(f"   Deadhead: {result.metrics.total_deadhead_km:.1f} km")
        print(f"   Emissions: {result.metrics.estimated_emissions_kg:.1f} kg CO2")
        print(f"   Duty Variance: {result.metrics.duty_variance_minutes:.1f} min")
        
        # Step 5: Create plan record using PlanService
        plan_service = PlanService()
        
        # Prepare objective weights
        weights = {
            'fleet_size': request.objective_weights.fleet_size if request.objective_weights else 0.4,
            'deadhead': request.objective_weights.deadhead if request.objective_weights else 0.3,
            'emissions': request.objective_weights.emissions if request.objective_weights else 0.2,
            'duty_variance': request.objective_weights.duty_variance if request.objective_weights else 0.1
        }
        
        plan = plan_service.create_plan(
            depot_id=request.depot_id,
            day_type=request.day_type,
            optimization_result=result,
            objective_weights=weights,
            db_session=db
        )
        
        db.commit()
        
        print(f"Plan created: {plan.plan_id}, version {plan.version}")
        
        # Step 6: Return response matching OptimizationResponse schema
        # CRITICAL: Capture depot totals for comparison
        total_vehicles_in_depot = len(vehicles)
        total_drivers_in_depot = len(drivers)
        
        print(f"📊 API Response Data:")
        print(f"   Depot Resources: {total_vehicles_in_depot} vehicles, {total_drivers_in_depot} drivers")
        print(f"   Optimized: {result.metrics.fleet_size} vehicles, {result.metrics.drivers_used} drivers")
        print(f"   Savings: {total_vehicles_in_depot - result.metrics.fleet_size} vehicles, {total_drivers_in_depot - result.metrics.drivers_used} drivers")
        
        response_data = {
            "plan_id": str(plan.plan_id),
            "version": plan.version,
            "depot_id": plan.depot_id,
            "status": plan.status,
            "metrics": {
                "fleet_size": result.metrics.fleet_size,
                "drivers_used": result.metrics.drivers_used,
                "total_deadhead_km": result.metrics.total_deadhead_km,
                "estimated_emissions_kg": result.metrics.estimated_emissions_kg,
                "duty_variance_minutes": result.metrics.duty_variance_minutes,
                "trips_covered": result.metrics.trips_covered,
                "trips_total": result.metrics.trips_total,
                "solver_time_seconds": result.solver_time_seconds
            },
            "depot_resources": {
                "total_vehicles": total_vehicles_in_depot,
                "total_drivers": total_drivers_in_depot
            },
            "created_at": plan.created_at.isoformat()
        }
        
        print(f"📤 Sending response:")
        print(f"   Response keys: {response_data.keys()}")
        print(f"   depot_resources in response: {'depot_resources' in response_data}")
        print(f"   depot_resources value: {response_data['depot_resources']}")
        
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Optimization error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get("/depots")
def list_depots(db: Session = Depends(get_db)):
    """
    List all available depots for optimization.
    """
    try:
        depots = db.query(Depot).all()
        return {
            "depots": [
                {
                    "depot_id": depot.depot_id,
                    "depot_name": depot.depot_name,
                    "latitude": float(depot.latitude),
                    "longitude": float(depot.longitude)
                }
                for depot in depots
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch depots: {str(e)}")
