"""Response Schemas

Pydantic models for API responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, time
from uuid import UUID


# ============================================================================
# Common/Shared Schemas
# ============================================================================

class OptimizationMetrics(BaseModel):
    """Optimization metrics for a plan"""
    fleet_size: int = Field(..., description="Number of vehicles used")
    drivers_used: int = Field(..., description="Number of drivers assigned")
    total_deadhead_km: float = Field(..., description="Total deadhead distance in kilometers")
    estimated_emissions_kg: float = Field(..., description="Estimated CO2 emissions in kilograms")
    duty_variance_minutes: float = Field(..., description="Variance in driver duty times (minutes)")
    trips_covered: int = Field(..., description="Number of trips covered")
    trips_total: int = Field(..., description="Total number of trips")
    solver_time_seconds: float = Field(..., description="Time taken by solver in seconds")


class DepotResources(BaseModel):
    """Total resources available at a depot"""
    total_vehicles: int = Field(..., description="Total vehicles available at depot")
    total_drivers: int = Field(..., description="Total drivers available at depot")


# ============================================================================
# CSV Upload Responses
# ============================================================================

class UploadResponse(BaseModel):
    """Response for CSV upload operation"""
    type: str = Field(..., description="Data type uploaded (routes, stops, vehicles, drivers, depots, timetable)")
    records_inserted: int = Field(..., description="Number of records successfully inserted")
    errors: List[str] = Field(default_factory=list, description="Validation or processing errors")
    warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "routes",
                "records_inserted": 45,
                "errors": [],
                "warnings": ["Route R101 has no associated trips in timetable"]
            }
        }


# ============================================================================
# Optimization Responses
# ============================================================================

class OptimizationResponse(BaseModel):
    """Response for optimization run"""
    plan_id: UUID = Field(..., description="Unique plan identifier")
    version: int = Field(..., description="Plan version number for this depot")
    depot_id: str = Field(..., description="Depot ID")
    status: str = Field(..., description="Plan status (PENDING, ACTIVE, ARCHIVED)")
    metrics: OptimizationMetrics = Field(..., description="Optimization metrics")
    depot_resources: DepotResources = Field(..., description="Total depot resources for comparison")
    created_at: datetime = Field(..., description="Plan creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "550e8400-e29b-41d4-a716-446655440000",
                "version": 5,
                "depot_id": "SWARGATE",
                "status": "PENDING",
                "metrics": {
                    "fleet_size": 45,
                    "drivers_used": 52,
                    "total_deadhead_km": 120.5,
                    "estimated_emissions_kg": 450.2,
                    "duty_variance_minutes": 15.3,
                    "solver_time_seconds": 87.2,
                    "trips_covered": 234,
                    "trips_total": 234
                },
                "depot_resources": {
                    "total_vehicles": 89,
                    "total_drivers": 106
                },
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


# ============================================================================
# Plan Management Responses
# ============================================================================

class TripDetail(BaseModel):
    """Trip details for assignments"""
    trip_id: str
    route_id: str
    start_time: time
    end_time: time
    start_stop_id: str
    end_stop_id: str


class VehicleAssignmentDetail(BaseModel):
    """Vehicle assignment details"""
    vehicle_id: str
    trips: List[TripDetail]
    deadhead_km: float


class DriverAssignmentDetail(BaseModel):
    """Driver assignment details"""
    driver_id: str
    trips: List[TripDetail]
    duty_hours: float
    break_minutes: int


class PlanResponse(BaseModel):
    """Full plan details with assignments"""
    plan_id: UUID
    version: int
    depot_id: str
    status: str
    day_type: str
    metrics: OptimizationMetrics
    objective_weights: Dict[str, float]
    vehicle_assignments: List[VehicleAssignmentDetail]
    driver_assignments: List[DriverAssignmentDetail]
    created_at: datetime
    deployed_at: Optional[datetime] = None


class PlanSummary(BaseModel):
    """Plan summary for list views"""
    plan_id: UUID
    version: int
    depot_id: str
    status: str
    day_type: str
    fleet_size: int
    total_deadhead_km: float
    estimated_emissions_kg: float
    created_at: datetime
    deployed_at: Optional[datetime] = None


class PlanListResponse(BaseModel):
    """Response for plan listing"""
    plans: List[PlanSummary]
    total: int
    limit: int
    offset: int


class ActivePlansResponse(BaseModel):
    """Response for active plans across all depots"""
    plans: List[PlanSummary]
    total: int


class DeploymentResponse(BaseModel):
    """Response for plan deployment"""
    success: bool
    message: str
    plan_id: UUID
    depot_id: str
    deployed_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Plan deployed successfully",
                "plan_id": "550e8400-e29b-41d4-a716-446655440000",
                "depot_id": "SWARGATE",
                "deployed_at": "2024-01-15T14:30:00Z"
            }
        }


class MetricDifference(BaseModel):
    """Metric difference between two plans"""
    fleet_size: int
    total_deadhead_km: float
    estimated_emissions_kg: float
    duty_variance_minutes: float


class PlanComparisonResponse(BaseModel):
    """Response for plan comparison"""
    plan_a: PlanSummary
    plan_b: PlanSummary
    differences: MetricDifference
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_a": {
                    "plan_id": "550e8400-e29b-41d4-a716-446655440000",
                    "version": 4,
                    "depot_id": "SWARGATE",
                    "status": "ACTIVE",
                    "day_type": "weekday",
                    "fleet_size": 47,
                    "total_deadhead_km": 125.8,
                    "estimated_emissions_kg": 462.3,
                    "created_at": "2024-01-14T10:30:00Z",
                    "deployed_at": "2024-01-14T15:00:00Z"
                },
                "plan_b": {
                    "plan_id": "660e8400-e29b-41d4-a716-446655440001",
                    "version": 5,
                    "depot_id": "SWARGATE",
                    "status": "PENDING",
                    "day_type": "weekday",
                    "fleet_size": 45,
                    "total_deadhead_km": 120.5,
                    "estimated_emissions_kg": 450.2,
                    "created_at": "2024-01-15T10:30:00Z",
                    "deployed_at": None
                },
                "differences": {
                    "fleet_size": -2,
                    "total_deadhead_km": -5.3,
                    "estimated_emissions_kg": -12.1,
                    "duty_variance_minutes": -2.1
                }
            }
        }


# ============================================================================
# Driver App Responses
# ============================================================================

class DriverScheduleTrip(BaseModel):
    """Trip details for driver schedule"""
    trip_id: str
    route_id: str
    route_name: str
    vehicle_id: str
    start_time: time
    end_time: time
    start_stop: str
    end_stop: str
    sequence_order: int


class DriverScheduleResponse(BaseModel):
    """Response for driver schedule query"""
    driver_id: str
    driver_name: str
    depot_id: str
    schedule: List[DriverScheduleTrip]
    total_duty_hours: float
    break_minutes: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "driver_id": "D01",
                "driver_name": "Rajesh Kumar",
                "depot_id": "SWARGATE",
                "schedule": [
                    {
                        "trip_id": "T1",
                        "route_id": "R401",
                        "route_name": "Swargate-Hadapsar",
                        "vehicle_id": "B101",
                        "start_time": "08:00:00",
                        "end_time": "08:45:00",
                        "start_stop": "Swargate",
                        "end_stop": "Hadapsar",
                        "sequence_order": 1
                    }
                ],
                "total_duty_hours": 7.5,
                "break_minutes": 45
            }
        }


# ============================================================================
# Error Responses
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid depot_id provided",
                "details": {
                    "depot_id": "INVALID_DEPOT",
                    "valid_depots": ["SWARGATE", "KATRAJ", "HADAPSAR"]
                }
            }
        }
