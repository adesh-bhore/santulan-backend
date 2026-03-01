"""Verify Plan Service Database Persistence

Check that plans and assignments are properly stored in the database.
"""

from app.database.db import SessionLocal
from app.models.plan_models import Plan, PlanVehicleAssignment, PlanDriverAssignment
from sqlalchemy import func

def verify_plans():
    """Verify plans are in database"""
    db = SessionLocal()
    
    try:
        # Count plans
        plan_count = db.query(func.count(Plan.plan_id)).scalar()
        print(f"Total plans in database: {plan_count}")
        
        # Get all plans
        plans = db.query(Plan).order_by(Plan.created_at.desc()).limit(5).all()
        
        print(f"\nRecent plans:")
        for plan in plans:
            print(f"\n  Plan ID: {plan.plan_id}")
            print(f"  Version: {plan.version}")
            print(f"  Depot: {plan.depot_id}")
            print(f"  Status: {plan.status}")
            print(f"  Day Type: {plan.day_type}")
            print(f"  Fleet Size: {plan.fleet_size}")
            print(f"  Trips: {plan.trips_covered}/{plan.trips_total}")
            print(f"  Created: {plan.created_at}")
            
            # Count assignments for this plan
            vehicle_assignments = db.query(func.count(PlanVehicleAssignment.assignment_id)).filter(
                PlanVehicleAssignment.plan_id == plan.plan_id
            ).scalar()
            
            driver_assignments = db.query(func.count(PlanDriverAssignment.assignment_id)).filter(
                PlanDriverAssignment.plan_id == plan.plan_id
            ).scalar()
            
            print(f"  Vehicle Assignments: {vehicle_assignments}")
            print(f"  Driver Assignments: {driver_assignments}")
            
            # Sample a few assignments
            if vehicle_assignments > 0:
                sample_vehicle = db.query(PlanVehicleAssignment).filter(
                    PlanVehicleAssignment.plan_id == plan.plan_id
                ).first()
                print(f"  Sample Vehicle Assignment: {sample_vehicle.vehicle_id} → {sample_vehicle.trip_id} (seq {sample_vehicle.sequence_order})")
            
            if driver_assignments > 0:
                sample_driver = db.query(PlanDriverAssignment).filter(
                    PlanDriverAssignment.plan_id == plan.plan_id
                ).first()
                print(f"  Sample Driver Assignment: {sample_driver.driver_id} → {sample_driver.trip_id} (seq {sample_driver.sequence_order})")
        
        # Verify version numbering per depot
        print(f"\n\nVersion numbering per depot:")
        depots = db.query(Plan.depot_id).distinct().all()
        for (depot_id,) in depots:
            versions = db.query(Plan.version).filter(Plan.depot_id == depot_id).order_by(Plan.version).all()
            version_list = [v[0] for v in versions]
            print(f"  {depot_id}: versions {version_list}")
        
        print(f"\n✅ Database verification complete!")
        
    finally:
        db.close()


if __name__ == "__main__":
    verify_plans()
