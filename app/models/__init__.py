"""Database Models

Exports all SQLAlchemy models for the application.
"""

from app.models.base_models import (
    Base,
    Depot,
    Route,
    Stop,
    Vehicle,
    Driver,
    Timetable
)

from app.models.plan_models import (
    Plan,
    PlanVehicleAssignment,
    PlanDriverAssignment,
    CurrentVehicleAssignment,
    CurrentDriverAssignment
)

__all__ = [
    # Base class
    "Base",
    
    # Layer A: Base Data
    "Depot",
    "Route",
    "Stop",
    "Vehicle",
    "Driver",
    "Timetable",
    
    # Layer B: Plan Tables
    "Plan",
    "PlanVehicleAssignment",
    "PlanDriverAssignment",
    
    # Layer C: Active Tables
    "CurrentVehicleAssignment",
    "CurrentDriverAssignment",
]
