"""Duty Management Schemas for Driver App"""

from pydantic import BaseModel
from typing import List, Optional


class TripSchedule(BaseModel):
    """Individual trip in schedule"""
    id: str
    tripNumber: int
    startPoint: str
    endPoint: str
    startTime: str
    endTime: str
    status: str  # scheduled, active, completed, delayed, cancelled
    is_unscheduled: Optional[bool] = False
    surge_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


class DutyInfo(BaseModel):
    """Duty assignment information"""
    id: str
    date: str
    routeNumber: str
    vehicleNumber: str
    shiftStart: str
    shiftEnd: str
    depot: str
    depotMarathi: Optional[str] = None
    totalTrips: int
    completedTrips: int = 0
    status: str  # active, upcoming, completed
    
    class Config:
        from_attributes = True


class TodayDutyResponse(BaseModel):
    """Today's duty response"""
    duty: DutyInfo
    schedule: List[TripSchedule]
    
    class Config:
        from_attributes = True
