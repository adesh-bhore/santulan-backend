"""Plan Service

CRUD operations for optimization plans.
Handles plan creation, retrieval, listing, and comparison.
"""

from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.plan_models import Plan, PlanVehicleAssignment, PlanDriverAssignment
from app.services.optimizer_fast import OptimizationResult


class PlanService:
    """Service for managing optimization plans"""
    
    def create_plan(
        self,
        depot_id: str,
        day_type: str,
        optimization_result: OptimizationResult,
        objective_weights: Dict[str, float],
        db_session: Session
    ) -> Plan:
        """
        Create new plan with next version number for depot.
        
        Process:
        1. Get max version for depot: SELECT MAX(version) WHERE depot_id = ?
        2. Create plan record with version = max + 1, status = PENDING
        3. Insert vehicle assignments to plan_vehicle_assignments
        4. Insert driver assignments to plan_driver_assignments
        5. Commit transaction
        6. Return plan object
        
        Args:
            depot_id: Depot identifier
            day_type: Day type (weekday/weekend)
            optimization_result: Result from optimizer
            objective_weights: Weights used for optimization
            db_session: Database session
            
        Returns:
            Created Plan object
        """
        # Step 1: Get next version number for depot
        max_version = db_session.query(func.max(Plan.version)).filter(
            Plan.depot_id == depot_id
        ).scalar()
        
        next_version = (max_version or 0) + 1
        
        # Step 2: Create plan record
        plan = Plan(
            version=next_version,
            depot_id=depot_id,
            status='PENDING',
            day_type=day_type,
            fleet_size=optimization_result.metrics.fleet_size,
            total_deadhead_km=optimization_result.metrics.total_deadhead_km,
            estimated_emissions_kg=optimization_result.metrics.estimated_emissions_kg,
            duty_variance_minutes=optimization_result.metrics.duty_variance_minutes,
            trips_covered=optimization_result.metrics.trips_covered,
            trips_total=optimization_result.metrics.trips_total,
            solver_time_seconds=optimization_result.solver_time_seconds,
            objective_weights=objective_weights
        )
        
        db_session.add(plan)
        db_session.flush()  # Get plan_id
        
        # Step 3: Insert vehicle assignments with deadhead calculation
        from app.models.base_models import Timetable, Stop
        from math import radians, sin, cos, sqrt, atan2
        
        def calculate_distance(lat1, lon1, lat2, lon2):
            """Calculate distance between two points using Haversine formula (in km)"""
            R = 6371  # Earth's radius in kilometers
            
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            
            return R * c
        
        for vehicle_id, trip_ids in optimization_result.vehicle_assignments.items():
            # Get all trips for this vehicle to calculate deadhead
            trips = db_session.query(Timetable).filter(
                Timetable.trip_id.in_(trip_ids)
            ).all()
            
            # Sort trips by start time
            trips_dict = {trip.trip_id: trip for trip in trips}
            sorted_trip_ids = sorted(trip_ids, key=lambda tid: trips_dict[tid].start_time)
            
            for sequence_order, trip_id in enumerate(sorted_trip_ids, start=1):
                deadhead_km = 0.0
                
                # Calculate deadhead from previous trip's end to this trip's start
                if sequence_order > 1:
                    prev_trip_id = sorted_trip_ids[sequence_order - 2]
                    prev_trip = trips_dict[prev_trip_id]
                    curr_trip = trips_dict[trip_id]
                    
                    # Get stop coordinates
                    prev_end_stop = db_session.query(Stop).filter(
                        Stop.stop_id == prev_trip.end_stop_id
                    ).first()
                    curr_start_stop = db_session.query(Stop).filter(
                        Stop.stop_id == curr_trip.start_stop_id
                    ).first()
                    
                    if prev_end_stop and curr_start_stop:
                        # Calculate distance if stops are different
                        if prev_trip.end_stop_id != curr_trip.start_stop_id:
                            deadhead_km = calculate_distance(
                                float(prev_end_stop.latitude),
                                float(prev_end_stop.longitude),
                                float(curr_start_stop.latitude),
                                float(curr_start_stop.longitude)
                            )
                
                assignment = PlanVehicleAssignment(
                    plan_id=plan.plan_id,
                    vehicle_id=vehicle_id,
                    trip_id=trip_id,
                    sequence_order=sequence_order,
                    deadhead_km=round(deadhead_km, 2)
                )
                db_session.add(assignment)
        
        # Step 4: Insert driver assignments
        # First, we need to get trip times to calculate actual duty hours
        from app.models.base_models import Timetable
        from datetime import datetime, time
        
        for driver_id, trip_ids in optimization_result.driver_assignments.items():
            # Get all trips for this driver to calculate shift times
            trips = db_session.query(Timetable).filter(
                Timetable.trip_id.in_(trip_ids)
            ).all()
            
            if not trips:
                continue
            
            # Calculate shift start and end
            shift_start = min(trip.start_time for trip in trips)
            shift_end = max(trip.end_time for trip in trips)
            
            # Calculate duty hours (time from first trip start to last trip end)
            # Convert time objects to datetime for calculation
            today = datetime.today().date()
            start_dt = datetime.combine(today, shift_start)
            end_dt = datetime.combine(today, shift_end)
            
            # Handle overnight shifts
            if end_dt < start_dt:
                end_dt = datetime.combine(today, shift_end) + timedelta(days=1)
            
            duty_hours = (end_dt - start_dt).total_seconds() / 3600.0
            
            # Calculate break time based on duty hours (Indian labor law)
            # 6-8 hours: 30 min break
            # 8-10 hours: 45 min break
            # 10+ hours: 60 min break (but this shouldn't happen with new constraints)
            if duty_hours >= 10:
                break_minutes = 60
            elif duty_hours >= 8:
                break_minutes = 45
            elif duty_hours >= 6:
                break_minutes = 30
            else:
                break_minutes = 0
            
            # Create assignments
            for sequence_order, trip_id in enumerate(trip_ids, start=1):
                assignment = PlanDriverAssignment(
                    plan_id=plan.plan_id,
                    driver_id=driver_id,
                    trip_id=trip_id,
                    sequence_order=sequence_order,
                    duty_hours=round(duty_hours, 1),  # Actual shift duration
                    break_minutes=break_minutes  # Calculated based on duty hours
                )
                db_session.add(assignment)
        
        # Step 5: Commit happens at caller level
        db_session.flush()
        
        return plan
    
    def get_plan(self, plan_id: UUID, db_session: Session) -> Optional[Plan]:
        """
        Retrieve plan with all assignments.
        
        Args:
            plan_id: Plan identifier
            db_session: Database session
            
        Returns:
            Plan object or None if not found
        """
        return db_session.query(Plan).filter(Plan.plan_id == plan_id).first()
    
    def list_plans(
        self,
        depot_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        db_session: Session = None
    ) -> List[Plan]:
        """
        List plans with filtering and pagination.
        
        Args:
            depot_id: Filter by depot (optional)
            status: Filter by status (optional)
            limit: Maximum number of results
            offset: Number of results to skip
            db_session: Database session
            
        Returns:
            List of Plan objects
        """
        query = db_session.query(Plan)
        
        if depot_id:
            query = query.filter(Plan.depot_id == depot_id)
        
        if status:
            query = query.filter(Plan.status == status)
        
        # Order by created_at descending (newest first)
        query = query.order_by(desc(Plan.created_at))
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_active_plans(self, db_session: Session) -> List[Plan]:
        """
        Get all active plans (one per depot).
        
        Args:
            db_session: Database session
            
        Returns:
            List of active Plan objects
        """
        return db_session.query(Plan).filter(Plan.status == 'ACTIVE').all()
    
    def compare_plans(
        self,
        plan_a_id: UUID,
        plan_b_id: UUID,
        db_session: Session
    ) -> Dict:
        """
        Compare metrics between two plans.
        
        Args:
            plan_a_id: First plan identifier
            plan_b_id: Second plan identifier
            db_session: Database session
            
        Returns:
            Dictionary with plan_a, plan_b, and differences
            
        Raises:
            ValueError: If either plan not found
        """
        plan_a = self.get_plan(plan_a_id, db_session)
        plan_b = self.get_plan(plan_b_id, db_session)
        
        if not plan_a:
            raise ValueError(f"Plan {plan_a_id} not found")
        if not plan_b:
            raise ValueError(f"Plan {plan_b_id} not found")
        
        # Calculate differences (plan_b - plan_a)
        differences = {
            'fleet_size': plan_b.fleet_size - plan_a.fleet_size,
            'total_deadhead_km': float(plan_b.total_deadhead_km - plan_a.total_deadhead_km),
            'estimated_emissions_kg': float(plan_b.estimated_emissions_kg - plan_a.estimated_emissions_kg),
            'duty_variance_minutes': float(plan_b.duty_variance_minutes - plan_a.duty_variance_minutes),
            'trips_covered': plan_b.trips_covered - plan_a.trips_covered,
            'solver_time_seconds': float(plan_b.solver_time_seconds - plan_a.solver_time_seconds)
        }
        
        return {
            'plan_a': {
                'plan_id': str(plan_a.plan_id),
                'version': plan_a.version,
                'depot_id': plan_a.depot_id,
                'status': plan_a.status,
                'metrics': {
                    'fleet_size': plan_a.fleet_size,
                    'total_deadhead_km': float(plan_a.total_deadhead_km),
                    'estimated_emissions_kg': float(plan_a.estimated_emissions_kg),
                    'duty_variance_minutes': float(plan_a.duty_variance_minutes),
                    'trips_covered': plan_a.trips_covered,
                    'trips_total': plan_a.trips_total,
                    'solver_time_seconds': float(plan_a.solver_time_seconds)
                }
            },
            'plan_b': {
                'plan_id': str(plan_b.plan_id),
                'version': plan_b.version,
                'depot_id': plan_b.depot_id,
                'status': plan_b.status,
                'metrics': {
                    'fleet_size': plan_b.fleet_size,
                    'total_deadhead_km': float(plan_b.total_deadhead_km),
                    'estimated_emissions_kg': float(plan_b.estimated_emissions_kg),
                    'duty_variance_minutes': float(plan_b.duty_variance_minutes),
                    'trips_covered': plan_b.trips_covered,
                    'trips_total': plan_b.trips_total,
                    'solver_time_seconds': float(plan_b.solver_time_seconds)
                }
            },
            'differences': differences
        }
    
    def get_active_plan_for_depot(
        self,
        depot_id: str,
        db_session: Session
    ) -> Optional[Plan]:
        """
        Get the active plan for a specific depot.
        
        Args:
            depot_id: Depot identifier
            db_session: Database session
            
        Returns:
            Active Plan object or None if no active plan
        """
        return db_session.query(Plan).filter(
            Plan.depot_id == depot_id,
            Plan.status == 'ACTIVE'
        ).first()
