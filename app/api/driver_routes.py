"""Driver App API Routes

Provides schedule information for drivers from active tables.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.db import get_db
from app.models.plan_models import CurrentDriverAssignment
from app.models.base_models import Timetable, Route, Stop, Driver, Vehicle, Depot
from app.models.plan_models import CurrentVehicleAssignment

router = APIRouter()


@router.get("/driver/{driver_id}/schedule")
def get_driver_schedule(
    driver_id: str,
    db: Session = Depends(get_db)
):
    """
    Get driver's current schedule from active tables.
    
    Returns complete schedule with trip details including:
    - Trip information (times, route, stops)
    - Vehicle assignment for each trip
    - Shift summary (start/end times, duty hours, breaks)
    
    Returns empty schedule if driver has no assignments (not an error).
    """
    try:
        # Get driver information
        driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
        
        # Get driver's current assignments from active tables
        assignments = db.query(CurrentDriverAssignment).filter(
            CurrentDriverAssignment.driver_id == driver_id
        ).order_by(CurrentDriverAssignment.sequence_order).all()
        
        # If no assignments, return empty schedule (not an error)
        if not assignments:
            return {
                "driver_id": driver_id,
                "driver_name": driver.driver_name if driver else driver_id,
                "depot_id": driver.depot_id if driver else None,
                "depot_name": None,
                "schedule": [],
                "total_duty_hours": 0.0,
                "break_minutes": 0,
                "shift_start": None,
                "shift_end": None
            }
        
        # Get depot information
        depot_id = assignments[0].depot_id
        depot = db.query(Depot).filter(Depot.depot_id == depot_id).first()
        
        # Build schedule with full trip details
        schedule = []
        shift_start = None
        shift_end = None
        
        for assignment in assignments:
            # Get trip details from timetable
            trip = db.query(Timetable).filter(
                Timetable.trip_id == assignment.trip_id
            ).first()
            
            if not trip:
                continue
            
            # Get route details
            route = db.query(Route).filter(Route.route_id == trip.route_id).first()
            
            # Get stop details
            start_stop = db.query(Stop).filter(Stop.stop_id == trip.start_stop_id).first()
            end_stop = db.query(Stop).filter(Stop.stop_id == trip.end_stop_id).first()
            
            # Get vehicle assignment for this trip
            vehicle_assignment = db.query(CurrentVehicleAssignment).filter(
                CurrentVehicleAssignment.depot_id == depot_id,
                CurrentVehicleAssignment.trip_id == assignment.trip_id
            ).first()
            
            # Get vehicle details
            vehicle = None
            if vehicle_assignment:
                vehicle = db.query(Vehicle).filter(
                    Vehicle.vehicle_id == vehicle_assignment.vehicle_id
                ).first()
            
            # Add trip to schedule
            schedule.append({
                "trip_id": trip.trip_id,
                "route_id": trip.route_id,
                "route_name": route.route_name if route else trip.route_id,
                "vehicle_id": vehicle_assignment.vehicle_id if vehicle_assignment else "Unknown",
                "vehicle_type": vehicle.vehicle_type if vehicle else "Unknown",
                "start_time": str(trip.start_time),
                "end_time": str(trip.end_time),
                "start_stop": start_stop.stop_name if start_stop else trip.start_stop_id,
                "end_stop": end_stop.stop_name if end_stop else trip.end_stop_id,
                "sequence_order": assignment.sequence_order
            })
            
            # Track shift start/end
            if shift_start is None or trip.start_time < shift_start:
                shift_start = trip.start_time
            if shift_end is None or trip.end_time > shift_end:
                shift_end = trip.end_time
        
        # Calculate total duty hours from shift start to end
        total_duty_hours = 0.0
        if shift_start and shift_end:
            from datetime import datetime, timedelta
            today = datetime.today().date()
            start_dt = datetime.combine(today, shift_start)
            end_dt = datetime.combine(today, shift_end)
            
            # Handle overnight shifts
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            total_duty_hours = round((end_dt - start_dt).total_seconds() / 3600.0, 1)
        
        # Build response
        return {
            "driver_id": driver_id,
            "driver_name": driver.driver_name if driver else driver_id,
            "depot_id": depot_id,
            "depot_name": depot.depot_name if depot else depot_id,
            "schedule": schedule,
            "total_duty_hours": total_duty_hours,
            "break_minutes": assignments[0].break_minutes if assignments else 0,
            "shift_start": str(shift_start) if shift_start else None,
            "shift_end": str(shift_end) if shift_end else None
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get driver schedule: {str(e)}"
        )
