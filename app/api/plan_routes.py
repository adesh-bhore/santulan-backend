"""Plan Management API Routes

Handles plan listing, retrieval, deployment, and comparison.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.database.db import get_db
from app.services.plan_service import PlanService
from app.services.deployment_service import DeploymentService
from app.models.plan_models import (
    Plan, 
    PlanVehicleAssignment, 
    PlanDriverAssignment
)
from app.models.base_models import Timetable, Route, Stop, Vehicle, Driver, Depot

router = APIRouter()


@router.get("/plans")
def list_plans(
    depot_id: Optional[str] = Query(None, description="Filter by depot ID"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, ACTIVE, ARCHIVED)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    List all plans with optional filtering and pagination.
    
    Returns summary view without assignments for performance.
    """
    try:
        plan_service = PlanService()
        
        plans = plan_service.list_plans(
            depot_id=depot_id,
            status=status,
            limit=limit,
            offset=offset,
            db_session=db
        )
        
        # Convert to response format
        result = []
        for plan in plans:
            result.append({
                "plan_id": str(plan.plan_id),
                "version": plan.version,
                "depot_id": plan.depot_id,
                "status": plan.status,
                "day_type": plan.day_type,
                "metrics": {
                    "fleet_size": plan.fleet_size,
                    "total_deadhead_km": float(plan.total_deadhead_km),
                    "estimated_emissions_kg": float(plan.estimated_emissions_kg),
                    "duty_variance_minutes": float(plan.duty_variance_minutes),
                    "trips_covered": plan.trips_covered,
                    "trips_total": plan.trips_total,
                    "solver_time_seconds": float(plan.solver_time_seconds)
                },
                "objective_weights": plan.objective_weights,
                "created_at": plan.created_at.isoformat(),
                "deployed_at": plan.deployed_at.isoformat() if plan.deployed_at else None
            })
        
        return {
            "plans": result,
            "total": len(result),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list plans: {str(e)}")


@router.get("/plans/active")
def get_active_plans(db: Session = Depends(get_db)):
    """
    Get all currently active plans (one per depot).
    
    Used for dashboard overview.
    """
    try:
        plan_service = PlanService()
        
        active_plans = plan_service.get_active_plans(db)
        
        # Get depot information for each plan
        result = []
        for plan in active_plans:
            depot = db.query(Depot).filter(Depot.depot_id == plan.depot_id).first()
            
            result.append({
                "plan_id": str(plan.plan_id),
                "version": plan.version,
                "depot_id": plan.depot_id,
                "depot_name": depot.depot_name if depot else plan.depot_id,
                "status": plan.status,
                "day_type": plan.day_type,
                "metrics": {
                    "fleet_size": plan.fleet_size,
                    "total_deadhead_km": float(plan.total_deadhead_km),
                    "estimated_emissions_kg": float(plan.estimated_emissions_kg),
                    "duty_variance_minutes": float(plan.duty_variance_minutes),
                    "trips_covered": plan.trips_covered,
                    "trips_total": plan.trips_total
                },
                "deployed_at": plan.deployed_at.isoformat() if plan.deployed_at else None
            })
        
        return {
            "active_plans": result,
            "total": len(result)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active plans: {str(e)}")


@router.get("/plans/{plan_id}")
def get_plan_details(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get full plan details including all assignments with trip information.
    
    This endpoint provides complete vehicle and driver assignments
    with joins to timetable, routes, and stops for full context.
    """
    try:
        plan_service = PlanService()
        
        # Get plan
        plan = plan_service.get_plan(plan_id, db)
        
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        
        # Get depot information
        depot = db.query(Depot).filter(Depot.depot_id == plan.depot_id).first()
        
        # Get vehicle assignments with full trip details
        vehicle_assignments_data = []
        vehicle_assignments = db.query(PlanVehicleAssignment).filter(
            PlanVehicleAssignment.plan_id == plan_id
        ).order_by(PlanVehicleAssignment.vehicle_id, PlanVehicleAssignment.sequence_order).all()
        
        # Group by vehicle
        vehicles_dict = {}
        for assignment in vehicle_assignments:
            if assignment.vehicle_id not in vehicles_dict:
                vehicles_dict[assignment.vehicle_id] = []
            vehicles_dict[assignment.vehicle_id].append(assignment)
        
        # Build vehicle assignment response with trip details
        for vehicle_id, assignments in vehicles_dict.items():
            vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
            
            trips = []
            total_deadhead = 0.0
            
            for assignment in assignments:
                # Get trip details from timetable
                trip = db.query(Timetable).filter(Timetable.trip_id == assignment.trip_id).first()
                
                if trip:
                    # Get route details
                    route = db.query(Route).filter(Route.route_id == trip.route_id).first()
                    
                    # Get stop details
                    start_stop = db.query(Stop).filter(Stop.stop_id == trip.start_stop_id).first()
                    end_stop = db.query(Stop).filter(Stop.stop_id == trip.end_stop_id).first()
                    
                    trips.append({
                        "trip_id": trip.trip_id,
                        "route_id": trip.route_id,
                        "route_name": route.route_name if route else trip.route_id,
                        "start_time": str(trip.start_time),
                        "end_time": str(trip.end_time),
                        "start_stop_id": trip.start_stop_id,
                        "start_stop_name": start_stop.stop_name if start_stop else trip.start_stop_id,
                        "end_stop_id": trip.end_stop_id,
                        "end_stop_name": end_stop.stop_name if end_stop else trip.end_stop_id,
                        "sequence_order": assignment.sequence_order,
                        "deadhead_km": float(assignment.deadhead_km)
                    })
                    
                    total_deadhead += float(assignment.deadhead_km)
            
            vehicle_assignments_data.append({
                "vehicle_id": vehicle_id,
                "vehicle_type": vehicle.vehicle_type if vehicle else "Unknown",
                "capacity": vehicle.capacity if vehicle else 0,
                "depot": depot.depot_name if depot else plan.depot_id,
                "trips": trips,
                "total_trips": len(trips),
                "total_deadhead_km": round(total_deadhead, 2),
                "status": "ASSIGNED"
            })
        
        # Get driver assignments with full trip details
        driver_assignments_data = []
        driver_assignments = db.query(PlanDriverAssignment).filter(
            PlanDriverAssignment.plan_id == plan_id
        ).order_by(PlanDriverAssignment.driver_id, PlanDriverAssignment.sequence_order).all()
        
        # Group by driver
        drivers_dict = {}
        for assignment in driver_assignments:
            if assignment.driver_id not in drivers_dict:
                drivers_dict[assignment.driver_id] = []
            drivers_dict[assignment.driver_id].append(assignment)
        
        # Build driver assignment response with trip details
        for driver_id, assignments in drivers_dict.items():
            driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
            
            trips = []
            shift_start = None
            shift_end = None
            
            for assignment in assignments:
                # Get trip details from timetable
                trip = db.query(Timetable).filter(Timetable.trip_id == assignment.trip_id).first()
                
                if trip:
                    # Get route details
                    route = db.query(Route).filter(Route.route_id == trip.route_id).first()
                    
                    # Get vehicle for this trip
                    vehicle_assignment = db.query(PlanVehicleAssignment).filter(
                        PlanVehicleAssignment.plan_id == plan_id,
                        PlanVehicleAssignment.trip_id == assignment.trip_id
                    ).first()
                    
                    trips.append({
                        "trip_id": trip.trip_id,
                        "route_id": trip.route_id,
                        "route_name": route.route_name if route else trip.route_id,
                        "vehicle_id": vehicle_assignment.vehicle_id if vehicle_assignment else "Unknown",
                        "start_time": str(trip.start_time),
                        "end_time": str(trip.end_time),
                        "sequence_order": assignment.sequence_order
                    })
                    
                    # Track shift start/end
                    if shift_start is None or trip.start_time < shift_start:
                        shift_start = trip.start_time
                    if shift_end is None or trip.end_time > shift_end:
                        shift_end = trip.end_time
            
            driver_assignments_data.append({
                "driver_id": driver_id,
                "driver_name": driver.driver_name if driver else driver_id,
                "depot": depot.depot_name if depot else plan.depot_id,
                "trips": trips,
                "shift_start": str(shift_start) if shift_start else None,
                "shift_end": str(shift_end) if shift_end else None,
                "total_duty_hours": float(assignments[0].duty_hours) if assignments else 0.0,
                "break_minutes": assignments[0].break_minutes if assignments else 0,
                "status": "ASSIGNED"
            })
        
        # Build complete response
        return {
            "plan_id": str(plan.plan_id),
            "version": plan.version,
            "depot_id": plan.depot_id,
            "depot_name": depot.depot_name if depot else plan.depot_id,
            "status": plan.status,
            "day_type": plan.day_type,
            "metrics": {
                "fleet_size": plan.fleet_size,
                "total_deadhead_km": float(plan.total_deadhead_km),
                "estimated_emissions_kg": float(plan.estimated_emissions_kg),
                "duty_variance_minutes": float(plan.duty_variance_minutes),
                "trips_covered": plan.trips_covered,
                "trips_total": plan.trips_total,
                "solver_time_seconds": float(plan.solver_time_seconds)
            },
            "objective_weights": plan.objective_weights,
            "vehicle_assignments": vehicle_assignments_data,
            "driver_assignments": driver_assignments_data,
            "created_at": plan.created_at.isoformat(),
            "deployed_at": plan.deployed_at.isoformat() if plan.deployed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get plan details: {str(e)}")


@router.post("/plans/{plan_id}/deploy")
def deploy_plan(
    plan_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Deploy a PENDING plan to active tables.
    
    This is an atomic operation that:
    - Archives the old ACTIVE plan for the depot
    - Activates the new plan
    - Copies all assignments to active tables
    """
    try:
        deployment_service = DeploymentService()
        
        # Deploy the plan (atomic transaction)
        result = deployment_service.deploy_plan(plan_id, db)
        
        # Commit the transaction
        db.commit()
        
        return result
        
    except ValueError as e:
        # Validation errors (plan not found, wrong status, etc.)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected errors
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@router.get("/plans/{plan_id}/compare")
def compare_plans(
    plan_id: UUID,
    compare_to_id: Optional[UUID] = Query(None, description="Plan ID to compare with (defaults to active plan for same depot)"),
    db: Session = Depends(get_db)
):
    """
    Compare two plans side-by-side.
    
    If compare_to_id is not provided, compares with the active plan
    for the same depot.
    """
    try:
        plan_service = PlanService()
        
        # Get the first plan
        plan_a = plan_service.get_plan(plan_id, db)
        if not plan_a:
            raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
        
        # Get the comparison plan
        if compare_to_id:
            plan_b = plan_service.get_plan(compare_to_id, db)
            if not plan_b:
                raise HTTPException(status_code=404, detail=f"Plan {compare_to_id} not found")
        else:
            # Compare with active plan for same depot
            plan_b = plan_service.get_active_plan_for_depot(plan_a.depot_id, db)
            if not plan_b:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No active plan found for depot {plan_a.depot_id}"
                )
        
        # Use plan service to compare
        comparison = plan_service.compare_plans(plan_a.plan_id, plan_b.plan_id, db)
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")
