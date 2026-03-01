"""Authentication Schemas for Driver App"""

from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """Driver login request - simplified to use driver_id"""
    driverId: str = Field(..., min_length=1, description="Driver ID (e.g., DRV_001)")
    password: str = Field(..., min_length=6, description="Password")


class RefreshTokenRequest(BaseModel):
    """Token refresh request"""
    refreshToken: str = Field(..., description="Refresh token")


class DriverProfile(BaseModel):
    """Driver profile information"""
    id: str
    name: str
    nameMarathi: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    depot: str
    depotMarathi: Optional[str] = None
    licenseNumber: Optional[str] = None
    rating: float = 0.0
    totalTrips: int = 0
    onTimePercent: float = 0.0
    safetyScore: int = 0
    dutyHoursThisMonth: float = 0.0
    dutyHoursTarget: float = 208.0
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response with tokens and profile"""
    token: str
    refreshToken: str
    expiresIn: int = 86400  # 24 hours
    driver: DriverProfile


class RefreshTokenResponse(BaseModel):
    """Token refresh response"""
    token: str
    expiresIn: int = 86400


class LogoutResponse(BaseModel):
    """Logout response"""
    success: bool = True
    message: str
    messageMarathi: str


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    message: str
    messageMarathi: str
    fields: Optional[dict] = None
    retryAfter: Optional[int] = None
