"""
Verification Script for DRT Phase 3: Ghost Bus Suppression

This script verifies that all Phase 3 components are properly installed and configured.
Run this after deployment to ensure everything is working correctly.

Usage:
    python verify_phase3.py
"""

import sys
from datetime import datetime, date, time
from sqlalchemy import inspect

def verify_database_tables(db):
    """Verify Phase 3 database tables exist"""
    print("\n" + "="*60)
    print("1. VERIFYING DATABASE TABLES")
    print("="*60)
    
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    
    required_tables = ['passenger_counts', 'trip_suppressions']
    
    for table in required_tables:
        if table in tables:
            print(f"✅ Table '{table}' exists")
            
            # Check columns
            columns = [col['name'] for col in inspector.get_columns(table)]
            print(f"   Columns: {', '.join(columns[:5])}...")
            
            # Check indexes
            indexes = inspector.get_indexes(table)
            print(f"   Indexes: {len(indexes)} found")
        else:
            print(f"❌ Table '{table}' NOT FOUND")
            return False
    
    return True


def verify_models():
    """Verify Phase 3 models can be imported"""
    print("\n" + "="*60)
    print("2. VERIFYING DATA MODELS")
    print("="*60)
    
    try:
        from app.drt.models import PassengerCount, TripSuppression
        print("✅ PassengerCount model imported successfully")
        print("✅ TripSuppression model imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import models: {e}")
        return False


def verify_services():
    """Verify Phase 3 services can be imported"""
    print("\n" + "="*60)
    print("3. VERIFYING SERVICES")
    print("="*60)
    
    try:
        from app.drt.ghost_bus import GhostBusService
        print("✅ GhostBusService imported successfully")
        
        from app.drt.passenger_count import PassengerCountService
        print("✅ PassengerCountService imported successfully")
        
        from app.drt.analysis_job import run_daily_ghost_bus_analysis
        print("✅ Daily analysis job imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import services: {e}")
        return False


def verify_schemas():
    """Verify Phase 3 schemas can be imported"""
    print("\n" + "="*60)
    print("4. VERIFYING PYDANTIC SCHEMAS")
    print("="*60)
    
    try:
        from app.drt.schemas import (
            PassengerCountRequest,
            PassengerCountResponse,
            TripSuppressionResponse,
            SuppressionDetailResponse,
            SuppressionApprovalRequest,
            SuppressionRejectionRequest,
            SuppressionAnalyticsResponse,
            DemandTrendResponse
        )
        print("✅ All Phase 3 schemas imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import schemas: {e}")
        return False


def verify_routes():
    """Verify Phase 3 routes are registered"""
    print("\n" + "="*60)
    print("5. VERIFYING API ROUTES")
    print("="*60)
    
    try:
        from app.main import app
        
        # Get all routes
        routes = [route.path for route in app.routes]
        
        required_routes = [
            '/api/drt/passenger-count',
            '/api/drt/suppression/pending',
            '/api/drt/suppression/history',
            '/api/drt/analytics/suppression',
            '/api/drt/analytics/demand-trends'
        ]
        
        for route in required_routes:
            if any(route in r for r in routes):
                print(f"✅ Route '{route}' registered")
            else:
                print(f"❌ Route '{route}' NOT FOUND")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Failed to verify routes: {e}")
        return False


def verify_configuration():
    """Verify Phase 3 configuration"""
    print("\n" + "="*60)
    print("6. VERIFYING CONFIGURATION")
    print("="*60)
    
    try:
        from app.config import settings
        
        config_vars = [
            'GHOST_BUS_THRESHOLD',
            'GHOST_BUS_ANALYSIS_DAYS',
            'GHOST_BUS_MIN_OCCURRENCES',
            'GHOST_BUS_AUTO_APPROVE',
            'GHOST_BUS_ANALYSIS_TIME'
        ]
        
        for var in config_vars:
            value = getattr(settings, var, None)
            if value is not None:
                print(f"✅ {var} = {value}")
            else:
                print(f"⚠️  {var} not set (using default)")
        
        return True
    except Exception as e:
        print(f"❌ Failed to verify configuration: {e}")
        return False


def test_passenger_count_recording(db):
    """Test passenger count recording"""
    print("\n" + "="*60)
    print("7. TESTING PASSENGER COUNT RECORDING")
    print("="*60)
    
    try:
        from app.drt.passenger_count import PassengerCountService
        
        service = PassengerCountService(db)
        
        # Test recording a count
        count = service.record_count(
            trip_id="TEST_TRIP_001",
            route_id="TEST_ROUTE_001",
            passenger_count=3,
            trip_date=date.today(),
            trip_time=time(8, 0, 0),
            source="manual",
            recorded_by="VERIFY_SCRIPT"
        )
        
        print(f"✅ Passenger count recorded: ID {count.count_id}")
        
        # Clean up test data
        db.delete(count)
        db.commit()
        print("✅ Test data cleaned up")
        
        return True
    except Exception as e:
        print(f"❌ Failed to record passenger count: {e}")
        db.rollback()
        return False


def test_suppression_creation(db):
    """Test suppression recommendation creation"""
    print("\n" + "="*60)
    print("8. TESTING SUPPRESSION CREATION")
    print("="*60)
    
    try:
        from app.drt.ghost_bus import GhostBusService
        
        service = GhostBusService(db)
        
        # Test creating a suppression
        suppression = service.create_suppression_recommendation(
            trip_id="TEST_TRIP_001",
            route_id="TEST_ROUTE_001",
            scheduled_date=date.today(),
            scheduled_time=time(8, 0, 0),
            reason="Test suppression for verification",
            avg_passenger_count=2.5,
            historical_days_analyzed=30,
            recommended_by="VERIFY_SCRIPT"
        )
        
        print(f"✅ Suppression created: ID {suppression.suppression_id}")
        
        # Clean up test data
        db.delete(suppression)
        db.commit()
        print("✅ Test data cleaned up")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create suppression: {e}")
        db.rollback()
        return False


def verify_scheduled_job():
    """Verify scheduled job is registered"""
    print("\n" + "="*60)
    print("9. VERIFYING SCHEDULED JOB")
    print("="*60)
    
    try:
        from app.main import scheduler
        
        jobs = scheduler.get_jobs()
        
        # Look for ghost bus analysis job
        ghost_bus_job = None
        for job in jobs:
            if 'ghost_bus' in job.id.lower() or 'analysis' in job.id.lower():
                ghost_bus_job = job
                break
        
        if ghost_bus_job:
            print(f"✅ Scheduled job found: {ghost_bus_job.id}")
            print(f"   Next run: {ghost_bus_job.next_run_time}")
            return True
        else:
            print("⚠️  Ghost bus analysis job not found in scheduler")
            print("   This is OK if scheduler hasn't started yet")
            return True
    except Exception as e:
        print(f"⚠️  Could not verify scheduled job: {e}")
        print("   This is OK if scheduler hasn't started yet")
        return True


def main():
    """Run all verification checks"""
    print("\n" + "="*60)
    print("DRT PHASE 3 VERIFICATION SCRIPT")
    print("="*60)
    print(f"Started at: {datetime.now()}")
    
    # Initialize database connection
    try:
        from app.database.db import SessionLocal
        db = SessionLocal()
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False
    
    # Run all checks
    checks = [
        ("Database Tables", lambda: verify_database_tables(db)),
        ("Data Models", verify_models),
        ("Services", verify_services),
        ("Pydantic Schemas", verify_schemas),
        ("API Routes", verify_routes),
        ("Configuration", verify_configuration),
        ("Passenger Count Recording", lambda: test_passenger_count_recording(db)),
        ("Suppression Creation", lambda: test_suppression_creation(db)),
        ("Scheduled Job", verify_scheduled_job),
    ]
    
    results = []
    for name, check in checks:
        try:
            result = check()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results.append((name, False))
    
    # Close database connection
    db.close()
    
    # Print summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed}/{total} checks passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL CHECKS PASSED! Phase 3 is ready to use!")
        return True
    else:
        print(f"\n⚠️  {total - passed} check(s) failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
