"""Error Response Schemas

Standardized error response formats for consistent API error handling.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ValidationError(BaseModel):
    """Single field validation error"""
    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Machine-readable error code")
    

class ErrorDetail(BaseModel):
    """Detailed error information"""
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Machine-readable error code (e.g., DEPOT_NOT_FOUND)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    validation_errors: Optional[List[ValidationError]] = Field(None, description="Field-level validation errors")


class ErrorResponse(BaseModel):
    """Standard error response format"""
    success: bool = Field(False, description="Always false for errors")
    error: ErrorDetail = Field(..., description="Error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "message": "Depot not found",
                    "code": "DEPOT_NOT_FOUND",
                    "details": {
                        "depot_id": "DEPOT_INVALID"
                    }
                },
                "request_id": "req_abc123",
                "timestamp": "2024-02-25T10:30:00Z"
            }
        }


# Common error codes
class ErrorCode:
    """Standard error codes"""
    
    # Validation errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    INVALID_CSV_DATA = "INVALID_CSV_DATA"
    
    # Not found errors (404)
    DEPOT_NOT_FOUND = "DEPOT_NOT_FOUND"
    PLAN_NOT_FOUND = "PLAN_NOT_FOUND"
    DRIVER_NOT_FOUND = "DRIVER_NOT_FOUND"
    VEHICLE_NOT_FOUND = "VEHICLE_NOT_FOUND"
    ROUTE_NOT_FOUND = "ROUTE_NOT_FOUND"
    
    # Conflict errors (409)
    PLAN_ALREADY_ACTIVE = "PLAN_ALREADY_ACTIVE"
    PLAN_ALREADY_DEPLOYED = "PLAN_ALREADY_DEPLOYED"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    
    # Business logic errors (422)
    INVALID_PLAN_STATUS = "INVALID_PLAN_STATUS"
    OPTIMIZATION_FAILED = "OPTIMIZATION_FAILED"
    INFEASIBLE_SOLUTION = "INFEASIBLE_SOLUTION"
    NO_TRIPS_FOUND = "NO_TRIPS_FOUND"
    NO_RESOURCES_FOUND = "NO_RESOURCES_FOUND"
    
    # Server errors (500)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    SOLVER_ERROR = "SOLVER_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
