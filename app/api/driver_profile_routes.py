"""Driver Profile API Routes for Driver App"""

from fastapi import APIRouter, Depends
from app.schemas.auth_schemas import DriverProfile
from app.api.auth_routes import get_current_driver

router = APIRouter()


@router.get("/profile", response_model=DriverProfile)
def get_driver_profile(
    current_driver: dict = Depends(get_current_driver)
):
    """
    Validate token and get current driver profile.
    
    This endpoint is used for:
    - Token validation
    - Biometric login (validate stored token)
    - Profile refresh
    
    Returns:
    - Complete driver profile with performance metrics
    
    Status codes:
    - 200: Profile returned successfully
    - 401: Unauthorized (invalid/expired token)
    """
    return current_driver
