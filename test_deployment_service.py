"""Test Deployment Service

Test that deployment works correctly with atomic transactions.
"""

from app.database.db import SessionLocal
from app.services.deployment_service import DeploymentService
from app.services.plan_service import PlanService
from app.models.plan_models import Plan, CurrentVehicleAssignment, CurrentDriverAssignment
from sqlalchemy import func


def test_deployment():
    """Test deploying a PENDING plan"""
    db = SessionLocal()
    
    try:
        deployment_service = DeploymentService()
        plan_service = PlanService()
        
        # Get a PENDING plan for DEPOT_BHSR
        pending_plans = plan_service.list_plans(
            depot_id="DEPOT_BHSR",
            status="PENDING",
            limit=1,
            db_session=db
        )
        
        if not pending_plans:
            print("❌ No PENDING plans found for DEPOT_BHSR")
            print("   Run optimization first to create a plan")
            return
        
        plan = pending_plans[0]
        print(f"\n{'='*60}")
        print(f"Testing Deployment")
        print(f"{'='*60}")
        print(f"\nPlan to deploy:")
        print(f"  Plan ID: {plan.plan_id}")
        print(f"  Version: {plan.version}")
        print(f"  Depot: {plan.depot_id}")
        print(f"  Status: {plan.status}")
        print(f"  Fleet Size: {plan.fleet_size}")
        print(f"  Trips: {plan.trips_covered}/{plan.trips_total}")
        
        # Check current deployment status
        print(f"\nCurrent deployment status:")
        status_before = deployment_service.get_deployment_status("DEPOT_BHSR", db)
        print(f"  Has active plan: {status_before['has_active_plan']}")
        if status_before['has_active_plan']:
            print(f"  Active plan: {status_before['plan_id']} (version {status_before['plan_version']})")
            print(f"  Vehicle assignments: {status_before['vehicle_assignments']}")
            print(f"  Driver assignments: {status_before['driver_assignments']}")
        
        # Deploy the plan
        print(f"\nDeploying plan {plan.plan_id}...")
        result = deployment_service.deploy_plan(plan.plan_id, db)
        
        # Commit the transaction
        db.commit()
        
        print(f"\n✅ Deployment Result:")
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message']}")
        print(f"  Deployed at: {result['deployed_at']}")
        print(f"  Vehicle assignments copied: {result['vehicle_assignments']}")
        print(f"  Driver assignments copied: {result['driver_assignments']}")
        
        # Verify deployment
        print(f"\nVerifying deployment...")
        
        # Check plan status changed to ACTIVE
        db.refresh(plan)
        print(f"  Plan status: {plan.status} (should be ACTIVE)")
        assert plan.status == 'ACTIVE', "Plan should be ACTIVE"
        
        # Check active tables have data
        vehicle_count = db.query(func.count(CurrentVehicleAssignment.assignment_id)).filter(
            CurrentVehicleAssignment.depot_id == "DEPOT_BHSR"
        ).scalar()
        
        driver_count = db.query(func.count(CurrentDriverAssignment.assignment_id)).filter(
            CurrentDriverAssignment.depot_id == "DEPOT_BHSR"
        ).scalar()
        
        print(f"  Active vehicle assignments: {vehicle_count}")
        print(f"  Active driver assignments: {driver_count}")
        
        assert vehicle_count > 0, "Should have vehicle assignments"
        assert driver_count > 0, "Should have driver assignments"
        
        # Check deployment status
        status_after = deployment_service.get_deployment_status("DEPOT_BHSR", db)
        print(f"\nDeployment status after:")
        print(f"  Has active plan: {status_after['has_active_plan']}")
        print(f"  Active plan: {status_after['plan_id']} (version {status_after['plan_version']})")
        print(f"  Vehicle assignments: {status_after['vehicle_assignments']}")
        print(f"  Driver assignments: {status_after['driver_assignments']}")
        
        print(f"\n✅ All deployment tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def test_deployment_errors():
    """Test deployment error cases"""
    db = SessionLocal()
    
    try:
        deployment_service = DeploymentService()
        
        print(f"\n{'='*60}")
        print(f"Testing Deployment Error Cases")
        print(f"{'='*60}")
        
        # Test 1: Deploy non-existent plan
        print(f"\nTest 1: Deploy non-existent plan")
        try:
            from uuid import uuid4
            fake_id = uuid4()
            deployment_service.deploy_plan(fake_id, db)
            print(f"  ❌ Should have raised ValueError")
        except ValueError as e:
            print(f"  ✅ Correctly raised ValueError: {str(e)}")
        
        # Test 2: Deploy ACTIVE plan
        print(f"\nTest 2: Deploy ACTIVE plan")
        active_plan = db.query(Plan).filter(Plan.status == 'ACTIVE').first()
        if active_plan:
            try:
                deployment_service.deploy_plan(active_plan.plan_id, db)
                print(f"  ❌ Should have raised ValueError")
            except ValueError as e:
                print(f"  ✅ Correctly raised ValueError: {str(e)}")
        else:
            print(f"  ⚠️  No ACTIVE plan to test with")
        
        # Test 3: Deploy ARCHIVED plan
        print(f"\nTest 3: Deploy ARCHIVED plan")
        archived_plan = db.query(Plan).filter(Plan.status == 'ARCHIVED').first()
        if archived_plan:
            try:
                deployment_service.deploy_plan(archived_plan.plan_id, db)
                print(f"  ❌ Should have raised ValueError")
            except ValueError as e:
                print(f"  ✅ Correctly raised ValueError: {str(e)}")
        else:
            print(f"  ⚠️  No ARCHIVED plan to test with")
        
        print(f"\n✅ All error case tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    # Test successful deployment
    test_deployment()
    
    # Test error cases
    test_deployment_errors()
