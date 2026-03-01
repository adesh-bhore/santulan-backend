"""Request Schemas

Pydantic models for API request validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


class ObjectiveWeights(BaseModel):
    """Objective weights for optimization"""
    fleet_size: float = Field(..., ge=0, le=1, description="Weight for fleet size minimization")
    deadhead: float = Field(..., ge=0, le=1, description="Weight for deadhead distance minimization")
    emissions: float = Field(..., ge=0, le=1, description="Weight for emissions minimization")
    duty_variance: float = Field(..., ge=0, le=1, description="Weight for duty variance minimization")
    
    @field_validator('fleet_size', 'deadhead', 'emissions', 'duty_variance')
    @classmethod
    def validate_weight_range(cls, v):
        """Ensure weights are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError('Weight must be between 0 and 1')
        return v
    
    def model_post_init(self, __context):
        """Validate that weights sum to 1.0"""
        total = self.fleet_size + self.deadhead + self.emissions + self.duty_variance
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError(f'Objective weights must sum to 1.0, got {total}')


class OptimizationRequest(BaseModel):
    """Request to run optimization for a depot"""
    depot_id: str = Field(..., min_length=1, max_length=50, description="Depot ID to optimize")
    day_type: Literal["weekday", "weekend"] = Field(..., description="Day type for optimization")
    objective_weights: ObjectiveWeights = Field(..., description="Weights for optimization objectives")
    
    class Config:
        json_schema_extra = {
            "example": {
                "depot_id": "SWARGATE",
                "day_type": "weekday",
                "objective_weights": {
                    "fleet_size": 0.4,
                    "deadhead": 0.3,
                    "emissions": 0.2,
                    "duty_variance": 0.1
                }
            }
        }


class DeploymentRequest(BaseModel):
    """Request to deploy a plan (plan_id comes from path parameter)"""
    # No body parameters needed - plan_id comes from URL path
    pass


class PlanListRequest(BaseModel):
    """Query parameters for listing plans"""
    depot_id: Optional[str] = Field(None, max_length=50, description="Filter by depot ID")
    status: Optional[Literal["PENDING", "ACTIVE", "ARCHIVED"]] = Field(None, description="Filter by status")
    limit: int = Field(10, ge=1, le=100, description="Number of results per page")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class PlanCompareRequest(BaseModel):
    """Query parameters for comparing plans"""
    compare_to_id: Optional[str] = Field(None, description="Plan ID to compare with (defaults to active plan for same depot)")
