"""Trip Management Schemas for Driver App"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LocationData(BaseModel):
    """GPS location data"""
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")


class StartTripRequest(BaseModel):
    """Request to start a trip"""
    actualStartTime: str = Field(..., description="ISO 8601 timestamp")
    location: LocationData


class EndTripRequest(BaseModel):
    """Request to end a trip"""
    actualEndTime: str = Field(..., description="ISO 8601 timestamp")
    location: LocationData
    passengerCount: int = Field(..., ge=0, description="Number of passengers")
    fareCollected: float = Field(..., ge=0, description="Total fare collected")
    notes: Optional[str] = Field(None, description="Additional notes")


class TripData(BaseModel):
    """Trip data in response"""
    id: str
    tripNumber: int
    status: str
    actualStartTime: Optional[str] = None
    actualEndTime: Optional[str] = None
    duration: Optional[int] = None
    startLocation: Optional[LocationData] = None
    endLocation: Optional[LocationData] = None
    passengerCount: Optional[int] = None
    fareCollected: Optional[float] = None


class DutySummary(BaseModel):
    """Duty summary data"""
    completedTrips: int
    totalTrips: int


class StartTripResponse(BaseModel):
    """Response for start trip"""
    success: bool = True
    trip: TripData
    message: str


class EndTripResponse(BaseModel):
    """Response for end trip"""
    success: bool = True
    trip: TripData
    duty: DutySummary
    message: str


class TripDetailResponse(BaseModel):
    """Detailed trip information"""
    id: str
    tripNumber: int
    routeNumber: str
    startPoint: str
    endPoint: str
    scheduledStartTime: str
    scheduledEndTime: str
    actualStartTime: Optional[str] = None
    actualEndTime: Optional[str] = None
    status: str
    vehicleNumber: str
    passengerCount: int = 0
    fareCollected: float = 0.0
