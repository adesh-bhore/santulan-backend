"""Database Initialization

Functions to create tables and seed demo data for development.
"""

from sqlalchemy.orm import Session
from app.database.db import engine


def create_tables():
    """
    Create all database tables.
    
    This should be called on application startup in development.
    In production, use Alembic migrations instead.
    """
    # Import all models to ensure they're registered with Base
    from app.models import Base
    import app.models.base_models
    import app.models.plan_models
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✓ Database tables created successfully")


def seed_demo_data(db: Session):
    """
    Seed database with demo data for development and testing.
    
    Args:
        db: Database session
    """
    from app.models.base_models import Depot, Route, Stop, Vehicle, Driver, Timetable
    from datetime import time
    
    # Check if data already exists
    if db.query(Depot).count() > 0:
        print("✓ Demo data already exists, skipping seed")
        return
    
    # Create demo depots
    depots = [
        Depot(depot_id="SWARGATE", depot_name="Swargate Depot", latitude=18.5018, longitude=73.8636),
        Depot(depot_id="KATRAJ", depot_name="Katraj Depot", latitude=18.4486, longitude=73.8594),
        Depot(depot_id="HADAPSAR", depot_name="Hadapsar Depot", latitude=18.5089, longitude=73.9260),
    ]
    db.add_all(depots)
    db.flush()
    
    # Create demo stops
    stops = [
        Stop(stop_id="STOP_SW", stop_name="Swargate", latitude=18.5018, longitude=73.8636),
        Stop(stop_id="STOP_KT", stop_name="Katraj", latitude=18.4486, longitude=73.8594),
        Stop(stop_id="STOP_HD", stop_name="Hadapsar", latitude=18.5089, longitude=73.9260),
        Stop(stop_id="STOP_SH", stop_name="Shivajinagar", latitude=18.5304, longitude=73.8503),
    ]
    db.add_all(stops)
    db.flush()
    
    # Create demo routes
    routes = [
        Route(route_id="R401", route_name="Swargate-Hadapsar", depot_id="SWARGATE"),
        Route(route_id="R205", route_name="Swargate-Katraj", depot_id="SWARGATE"),
        Route(route_id="R301", route_name="Katraj-Shivajinagar", depot_id="KATRAJ"),
    ]
    db.add_all(routes)
    db.flush()
    
    # Create demo vehicles
    vehicles = [
        Vehicle(vehicle_id="B101", vehicle_type="Standard", capacity=40, depot_id="SWARGATE", emission_factor=2.68),
        Vehicle(vehicle_id="B102", vehicle_type="Standard", capacity=40, depot_id="SWARGATE", emission_factor=2.68),
        Vehicle(vehicle_id="B103", vehicle_type="Standard", capacity=40, depot_id="SWARGATE", emission_factor=2.68),
        Vehicle(vehicle_id="B201", vehicle_type="Standard", capacity=40, depot_id="KATRAJ", emission_factor=2.68),
        Vehicle(vehicle_id="B202", vehicle_type="Standard", capacity=40, depot_id="KATRAJ", emission_factor=2.68),
    ]
    db.add_all(vehicles)
    db.flush()
    
    # Create demo drivers
    drivers = [
        Driver(driver_id="D01", driver_name="Rajesh Kumar", depot_id="SWARGATE", max_duty_hours=8.0),
        Driver(driver_id="D02", driver_name="Amit Patil", depot_id="SWARGATE", max_duty_hours=8.0),
        Driver(driver_id="D03", driver_name="Suresh Deshmukh", depot_id="SWARGATE", max_duty_hours=8.0),
        Driver(driver_id="D04", driver_name="Vijay Shinde", depot_id="KATRAJ", max_duty_hours=8.0),
        Driver(driver_id="D05", driver_name="Prakash Jadhav", depot_id="KATRAJ", max_duty_hours=8.0),
    ]
    db.add_all(drivers)
    db.flush()
    
    # Create demo timetable
    timetable = [
        Timetable(trip_id="T1", route_id="R401", start_time=time(6, 0), end_time=time(6, 45), 
                 start_stop_id="STOP_SW", end_stop_id="STOP_HD", day_type="weekday"),
        Timetable(trip_id="T2", route_id="R205", start_time=time(7, 0), end_time=time(7, 40), 
                 start_stop_id="STOP_SW", end_stop_id="STOP_KT", day_type="weekday"),
        Timetable(trip_id="T3", route_id="R401", start_time=time(8, 0), end_time=time(8, 45), 
                 start_stop_id="STOP_SW", end_stop_id="STOP_HD", day_type="weekday"),
        Timetable(trip_id="T4", route_id="R205", start_time=time(9, 0), end_time=time(9, 40), 
                 start_stop_id="STOP_SW", end_stop_id="STOP_KT", day_type="weekday"),
        Timetable(trip_id="T5", route_id="R301", start_time=time(7, 30), end_time=time(8, 15), 
                 start_stop_id="STOP_KT", end_stop_id="STOP_SH", day_type="weekday"),
    ]
    db.add_all(timetable)
    
    db.commit()
    print("✓ Demo data seeded successfully")
