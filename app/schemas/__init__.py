"""Pydantic Schemas

Exports all request and response schemas for the API.
"""

from app.schemas.request_schemas import (
    ObjectiveWeights,
    OptimizationRequest,
    DeploymentRequest,
    PlanListRequest,
    PlanCompareRequest,
)

from app.schemas.response_schemas import (
    # Common
    OptimizationMetrics,
    
    # CSV Upload
    UploadResponse,
    
    # Optimization
    OptimizationResponse,
    
    # Plan Management
    TripDetail,
    VehicleAssignmentDetail,
    DriverAssignmentDetail,
    PlanResponse,
    PlanSummary,
    PlanListResponse,
    ActivePlansResponse,
    DeploymentResponse,
    MetricDifference,
    PlanComparisonResponse,
    
    # Driver App
    DriverScheduleTrip,
    DriverScheduleResponse,
    
    # Errors
    ErrorResponse,
)

__all__ = [
    # Request Schemas
    "ObjectiveWeights",
    "OptimizationRequest",
    "DeploymentRequest",
    "PlanListRequest",
    "PlanCompareRequest",
    
    # Response Schemas - Common
    "OptimizationMetrics",
    
    # Response Schemas - CSV Upload
    "UploadResponse",
    
    # Response Schemas - Optimization
    "OptimizationResponse",
    
    # Response Schemas - Plan Management
    "TripDetail",
    "VehicleAssignmentDetail",
    "DriverAssignmentDetail",
    "PlanResponse",
    "PlanSummary",
    "PlanListResponse",
    "ActivePlansResponse",
    "DeploymentResponse",
    "MetricDifference",
    "PlanComparisonResponse",
    
    # Response Schemas - Driver App
    "DriverScheduleTrip",
    "DriverScheduleResponse",
    
    # Response Schemas - Errors
    "ErrorResponse",
]
