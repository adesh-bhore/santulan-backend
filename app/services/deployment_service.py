"""Deployment Service

Atomic deployment of plans to active tables.
Handles the critical transition from PENDING plans to ACTIVE deployment.
"""

from typing import Dict
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.plan_models import (
    Plan, 
    PlanVehicleAssignment, 
    PlanDriverAssignment,
    CurrentVehicleAssignment,
    CurrentDriverAssignment
)


class DeploymentService:
    """Service for atomic plan deployment"""
    
    def deploy_plan(self, plan_id: UUID, db_session: Session) -> Dict:
        """
        Deploy plan atomically (single transaction).
        
        Process (all within one transaction):
        1. Verify plan exists and status = PENDING
        2. Get plan's depot_id
        3. Archive old active plan for depot
        4. Activate new plan
        5. Clear active tables for depot
        6. Copy assignments to active tables with depot_id
        7. COMMIT (or ROLLBACK on any error)
        
        Args:
            plan_id: UUID of the plan to deploy
            db_session: Database session (transaction managed by caller)
            
        Returns:
            Dictionary with success status, message, and deployed_at timestamp
            
        Raises:
            ValueError: If plan not found, not PENDING, or other validation errors
        """
        try:
            # Step 1: Verify plan exists and status = PENDING
            plan = db_session.query(Plan).filter(Plan.plan_id == plan_id).first()
            
            if not plan:
                raise ValueError(f"Plan {plan_id} not found")
            
            if plan.status != 'PENDING':
                raise ValueError(
                    f"Cannot deploy plan with status '{plan.status}'. "
                    f"Only PENDING plans can be deployed."
                )
            
            # Step 2: Get plan's depot_id
            depot_id = plan.depot_id
            
            print(f"Deploying plan {plan_id} for depot {depot_id}...")
            
            # Step 3: Archive old active plan for depot
            old_active_plans = db_session.query(Plan).filter(
                Plan.depot_id == depot_id,
                Plan.status == 'ACTIVE'
            ).all()
            
            for old_plan in old_active_plans:
                old_plan.status = 'ARCHIVED'
                print(f"  Archived old plan {old_plan.plan_id} (version {old_plan.version})")
            
            # Step 4: Activate new plan
            plan.status = 'ACTIVE'
            plan.deployed_at = datetime.utcnow()
            deployed_at = plan.deployed_at
            
            print(f"  Activated plan {plan_id} (version {plan.version})")
            
            # Step 5: Clear active tables for depot
            deleted_vehicles = db_session.query(CurrentVehicleAssignment).filter(
                CurrentVehicleAssignment.depot_id == depot_id
            ).delete()
            
            deleted_drivers = db_session.query(CurrentDriverAssignment).filter(
                CurrentDriverAssignment.depot_id == depot_id
            ).delete()
            
            print(f"  Cleared active tables: {deleted_vehicles} vehicles, {deleted_drivers} drivers")
            
            # Step 6: Copy assignments to active tables with depot_id
            # Get all vehicle assignments for this plan
            vehicle_assignments = db_session.query(PlanVehicleAssignment).filter(
                PlanVehicleAssignment.plan_id == plan_id
            ).all()
            
            # Get all driver assignments for this plan
            driver_assignments = db_session.query(PlanDriverAssignment).filter(
                PlanDriverAssignment.plan_id == plan_id
            ).all()
            
            # Insert vehicle assignments to current_vehicle_assignments
            for assignment in vehicle_assignments:
                current_assignment = CurrentVehicleAssignment(
                    depot_id=depot_id,
                    vehicle_id=assignment.vehicle_id,
                    trip_id=assignment.trip_id,
                    sequence_order=assignment.sequence_order,
                    deadhead_km=assignment.deadhead_km,
                    deployed_at=deployed_at
                )
                db_session.add(current_assignment)
            
            # Insert driver assignments to current_driver_assignments
            for assignment in driver_assignments:
                current_assignment = CurrentDriverAssignment(
                    depot_id=depot_id,
                    driver_id=assignment.driver_id,
                    trip_id=assignment.trip_id,
                    sequence_order=assignment.sequence_order,
                    duty_hours=assignment.duty_hours,
                    break_minutes=assignment.break_minutes,
                    deployed_at=deployed_at
                )
                db_session.add(current_assignment)
            
            print(f"  Copied {len(vehicle_assignments)} vehicle assignments")
            print(f"  Copied {len(driver_assignments)} driver assignments")
            
            # Flush to ensure all changes are staged
            db_session.flush()
            
            # Step 7: Commit happens at caller level
            print(f"✅ Deployment successful for plan {plan_id}")
            
            return {
                'success': True,
                'message': f'Plan {plan_id} deployed successfully to depot {depot_id}',
                'deployed_at': deployed_at.isoformat(),
                'depot_id': depot_id,
                'plan_version': plan.version,
                'vehicle_assignments': len(vehicle_assignments),
                'driver_assignments': len(driver_assignments)
            }
            
        except ValueError as e:
            # Validation errors - don't rollback, just raise
            print(f"❌ Deployment validation error: {str(e)}")
            raise
            
        except Exception as e:
            # Unexpected errors - log and raise
            print(f"❌ Deployment error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Deployment failed: {str(e)}")
    
    def get_active_plan_for_depot(self, depot_id: str, db_session: Session) -> Plan:
        """
        Get the currently active plan for a depot.
        
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
    
    def get_deployment_status(self, depot_id: str, db_session: Session) -> Dict:
        """
        Get deployment status for a depot.
        
        Args:
            depot_id: Depot identifier
            db_session: Database session
            
        Returns:
            Dictionary with deployment status information
        """
        active_plan = self.get_active_plan_for_depot(depot_id, db_session)
        
        if not active_plan:
            return {
                'depot_id': depot_id,
                'has_active_plan': False,
                'message': f'No active plan deployed for depot {depot_id}'
            }
        
        # Count active assignments
        vehicle_count = db_session.query(CurrentVehicleAssignment).filter(
            CurrentVehicleAssignment.depot_id == depot_id
        ).count()
        
        driver_count = db_session.query(CurrentDriverAssignment).filter(
            CurrentDriverAssignment.depot_id == depot_id
        ).count()
        
        return {
            'depot_id': depot_id,
            'has_active_plan': True,
            'plan_id': str(active_plan.plan_id),
            'plan_version': active_plan.version,
            'deployed_at': active_plan.deployed_at.isoformat() if active_plan.deployed_at else None,
            'vehicle_assignments': vehicle_count,
            'driver_assignments': driver_count,
            'fleet_size': active_plan.fleet_size,
            'trips_covered': active_plan.trips_covered
        }
