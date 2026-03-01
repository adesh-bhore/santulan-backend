"""Duty Management API Routes for Driver App"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services.duty_service import DutyService
from app.schemas.duty_schemas import TodayDutyResponse
from app.api.auth_routes import get_current_driver

router = APIRouter()


@router.get("/today", response_model=TodayDutyResponse)
def get_today_duty(
    current_driver: dict = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """
    Get today's duty assignment and trip schedule for the authenticated driver.
    
    Returns:
    - Duty information (route, vehicle, shift times, etc.)
    - Complete trip schedule with status
    
    Status codes:
    - 200: Duty found and returned
    - 401: Unauthorized (invalid/expired token)
    - 404: No duty assigned for today
    - 500: Server error
    """
    try:
        driver_id = current_driver["id"]
        
        # Get today's duty
        duty_data = DutyService.get_today_duty(db, driver_id)
        
        if not duty_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NO_DUTY_ASSIGNED",
                    "message": "No duty assigned for today",
                    "messageMarathi": "आजसाठी कोणतेही कर्तव्य नियुक्त केलेले नाही"
                }
            )
        
        return duty_data
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get today duty error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "messageMarathi": "एक अनपेक्षित त्रुटी आली. कृपया पुन्हा प्रयत्न करा."
            }
        )
