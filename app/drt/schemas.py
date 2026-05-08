"""Schemas for Commuter DRT Ping System"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date, time


class CommuterRegisterRequest(BaseModel):
    """Commuter registration request"""
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number")
    name: Optional[str] = Field(None, max_length=200, description="Commuter name")
    email: Optional[str] = Field(None, max_length=100, description="Email address")
    password: Optional[str] = Field(None, min_length=6, description="Password (optional)")
    
    @validator('phone')
    def validate_phone(cls, v):
        # Remove spaces and special characters
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) < 10:
            raise ValueError('Phone number must have at least 10 digits')
        return cleaned


class CommuterLoginRequest(BaseModel):
    """Commuter login request"""
    phone: str = Field(..., min_length=10, description="Phone number")
    password: str = Field(..., min_length=6, description="Password")


class CommuterResponse(BaseModel):
    """Commuter profile response"""
    commuter_id: str
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    total_pings: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class CommuterAuthResponse(BaseModel):
    """Commuter authentication response"""
    token: str
    commuter: CommuterResponse
    expiresIn: int = 86400


class PingRequest(BaseModel):
    """Commuter ping request"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    ping_metadata: Optional[dict] = Field(None, description="Additional metadata")


class PingResponse(BaseModel):
    """Ping response"""
    ping_id: int
    commuter_id: str
    latitude: float
    longitude: float
    detected_stop_id: Optional[str] = None
    detected_stop_name: Optional[str] = None
    distance_to_stop_m: Optional[float] = None
    ping_time: datetime
    status: str
    message: str
    
    class Config:
        from_attributes = True


class PingHistoryResponse(BaseModel):
    """Ping history response"""
    ping_id: int
    latitude: float
    longitude: float
    detected_stop_id: Optional[str] = None
    detected_stop_name: Optional[str] = None
    distance_to_stop_m: Optional[float] = None
    ping_time: datetime
    status: str
    
    class Config:
        from_attributes = True


class PingStatsResponse(BaseModel):
    """Ping statistics response"""
    total_pings: int
    pending_pings: int
    processed_pings: int
    surge_triggered_pings: int


# Phase 2: Surge Detection Schemas

class SurgeEventResponse(BaseModel):
    """Surge event response"""
    surge_id: int
    stop_id: str
    stop_name: Optional[str] = None
    depot_id: Optional[str] = None  # Added for filtering surge resources
    route_ids: list
    ping_count: int
    detected_at: datetime
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


class SurgeDetailResponse(BaseModel):
    """Detailed surge event with ping locations"""
    surge_id: int
    stop_id: str
    stop_name: Optional[str] = None
    route_ids: list
    ping_count: int
    detected_at: datetime
    status: str
    pings: List[dict]  # List of ping details with commuter info
    
    class Config:
        from_attributes = True


class SurgeApprovalRequest(BaseModel):
    """Surge approval request"""
    route_id: str = Field(..., description="Route ID to dispatch")
    vehicle_id: str = Field(..., description="Vehicle ID to assign")
    driver_id: str = Field(..., description="Driver ID to assign")
    start_stop_id: str = Field(..., description="Start stop ID")
    end_stop_id: str = Field(..., description="End stop ID")
    scheduled_start_time: datetime = Field(..., description="Scheduled start time")
    notes: Optional[str] = Field(None, description="Additional notes")


class SurgeRejectionRequest(BaseModel):
    """Surge rejection request"""
    reason: str = Field(..., min_length=10, description="Reason for rejection")


class UnscheduledTripResponse(BaseModel):
    """Unscheduled trip response"""
    unscheduled_trip_id: int
    surge_id: int
    route_id: str
    vehicle_id: str
    driver_id: str
    depot_id: str
    start_stop_id: str
    end_stop_id: str
    scheduled_start_time: datetime
    scheduled_end_time: datetime
    status: str
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    passenger_count: Optional[int] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True



# ========================================
# Phase 3: Ghost Bus Suppression Schemas
# ========================================

class PassengerCountRequest(BaseModel):
    """Request to record passenger count"""
    trip_id: str
    route_id: str
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    passenger_count: int
    boarding_count: Optional[int] = None
    alighting_count: Optional[int] = None
    trip_date: date
    trip_time: time
    source: str = 'manual'  # manual, automatic, estimated
    recorded_by: Optional[str] = None


class PassengerCountResponse(BaseModel):
    """Response for passenger count"""
    count_id: int
    trip_id: str
    route_id: str
    passenger_count: int
    trip_date: date
    trip_time: time
    source: str
    recorded_at: datetime
    
    class Config:
        from_attributes = True


class SuppressionRecommendationRequest(BaseModel):
    """Request to create suppression recommendation"""
    trip_id: str
    route_id: str
    scheduled_date: date
    scheduled_time: time
    suppression_reason: str
    avg_passenger_count: Optional[float] = None
    historical_days_analyzed: Optional[int] = None


class SuppressionApprovalRequest(BaseModel):
    """Request to approve suppression"""
    notes: Optional[str] = None


class SuppressionRejectionRequest(BaseModel):
    """Request to reject suppression"""
    reason: str


class TripSuppressionResponse(BaseModel):
    """Response for trip suppression"""
    suppression_id: int
    trip_id: str
    route_id: str
    scheduled_date: date
    scheduled_time: time
    suppression_reason: str
    avg_passenger_count: Optional[float]
    historical_days_analyzed: Optional[int]
    status: str
    recommended_by: Optional[str]
    recommended_at: Optional[datetime]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    rejected_by: Optional[str]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    executed_at: Optional[datetime]
    vehicle_freed: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SuppressionDetailResponse(BaseModel):
    """Detailed suppression information"""
    suppression: TripSuppressionResponse
    historical_counts: List[PassengerCountResponse]
    route_name: Optional[str]
    avg_count_last_30_days: Optional[float]
    
    class Config:
        from_attributes = True


class SuppressionAnalyticsResponse(BaseModel):
    """Suppression analytics"""
    total_suppressions: int
    approved_suppressions: int
    rejected_suppressions: int
    executed_suppressions: int
    approval_rate: float
    vehicles_freed: int
    avg_passenger_count: float
    date_range: dict
    
    class Config:
        from_attributes = True


class DemandTrendResponse(BaseModel):
    """Demand trend data"""
    route_id: str
    route_name: Optional[str]
    date: date
    avg_passenger_count: float
    trip_count: int
    
    class Config:
        from_attributes = True
