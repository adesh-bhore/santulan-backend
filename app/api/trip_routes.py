"""Trip Management API Routes for Driver App"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.db import get_db
from app.services.trip_service import TripService
from app.api.auth_routes import get_current_driver
from app.schemas.trip_schemas import (
    StartTripRequest, StartTripResponse,
    EndTripRequest, EndTripResponse,
    TripDetailResponse
)

router = APIRouter()
security = HTTPBearer()


@router.post("/trips/{trip_id}/start", response_model=StartTripResponse)
async def start_trip(
    trip_id: str,
    request: StartTripRequest,
    db: Session = Depends(get_db),
    current_driver: dict = Depends(get_current_driver)
):
    """
    Start a trip. Called when driver clicks "Start Trip" button.
    
    Validates:
    - Trip exists and belongs to driver
    - Trip not already started
    - Previous trips are completed (sequential order)
    - Only one trip can be active at a time
    """
    try:
        driver_id = current_driver["id"]
        
        # Parse ISO timestamp
        actual_start_time = datetime.fromisoformat(request.actualStartTime.replace('Z', '+00:00'))
        
        # Convert location to dict
        location = {
            "latitude": request.location.latitude,
            "longitude": request.location.longitude
        }
        
        # Start the trip
        result = TripService.start_trip(
            db=db,
            trip_id=trip_id,
            driver_id=driver_id,
            actual_start_time=actual_start_time,
            location=location
        )
        
        return result
    
    except ValueError as e:
        error_code = str(e)
        
        if error_code == "TRIP_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "TRIP_NOT_FOUND",
                    "message": "Trip not found",
                    "messageMarathi": "ट्रिप सापडली नाही"
                }
            )
        elif error_code == "TRIP_ALREADY_STARTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "TRIP_ALREADY_STARTED",
                    "message": "Trip already started",
                    "messageMarathi": "ट्रिप आधीच सुरू झाली आहे"
                }
            )
        elif error_code == "TRIP_ALREADY_COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "TRIP_ALREADY_COMPLETED",
                    "message": "Trip already completed",
                    "messageMarathi": "ट्रिप आधीच पूर्ण झाली आहे"
                }
            )
        elif error_code == "ANOTHER_TRIP_ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ANOTHER_TRIP_ACTIVE",
                    "message": "Another trip is already active",
                    "messageMarathi": "दुसरी ट्रिप आधीच सक्रिय आहे"
                }
            )
        elif error_code == "SEQUENTIAL_ORDER_VIOLATION":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "SEQUENTIAL_ORDER_VIOLATION",
                    "message": "Previous trip must be completed first",
                    "messageMarathi": "मागील ट्रिप प्रथम पूर्ण करणे आवश्यक आहे"
                }
            )
        else:
            raise
    
    except Exception as e:
        print(f"Start trip error: {str(e)}")
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


@router.post("/trips/{trip_id}/end", response_model=EndTripResponse)
async def end_trip(
    trip_id: str,
    request: EndTripRequest,
    db: Session = Depends(get_db),
    current_driver: dict = Depends(get_current_driver)
):
    """
    End a trip. Called when driver clicks "End Trip" button.
    
    Records:
    - Actual end time
    - End location
    - Passenger count
    - Fare collected
    - Optional notes
    """
    try:
        driver_id = current_driver["id"]
        
        # Parse ISO timestamp
        actual_end_time = datetime.fromisoformat(request.actualEndTime.replace('Z', '+00:00'))
        
        # Convert location to dict
        location = {
            "latitude": request.location.latitude,
            "longitude": request.location.longitude
        }
        
        # End the trip
        result = TripService.end_trip(
            db=db,
            trip_id=trip_id,
            driver_id=driver_id,
            actual_end_time=actual_end_time,
            location=location,
            passenger_count=request.passengerCount,
            fare_collected=request.fareCollected,
            notes=request.notes
        )
        
        return result
    
    except ValueError as e:
        error_code = str(e)
        
        if error_code == "TRIP_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "TRIP_NOT_FOUND",
                    "message": "Trip not found",
                    "messageMarathi": "ट्रिप सापडली नाही"
                }
            )
        elif error_code == "TRIP_NOT_STARTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "TRIP_NOT_STARTED",
                    "message": "Trip not started yet",
                    "messageMarathi": "ट्रिप अद्याप सुरू झाली नाही"
                }
            )
        else:
            raise
    
    except Exception as e:
        print(f"End trip error: {str(e)}")
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


@router.get("/trips/{trip_id}", response_model=TripDetailResponse)
async def get_trip(
    trip_id: str,
    db: Session = Depends(get_db),
    current_driver: dict = Depends(get_current_driver)
):
    """
    Get details of a specific trip.
    """
    try:
        driver_id = current_driver["id"]
        
        trip_details = TripService.get_trip_details(db, trip_id, driver_id)
        
        if not trip_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "TRIP_NOT_FOUND",
                    "message": "Trip not found",
                    "messageMarathi": "ट्रिप सापडली नाही"
                }
            )
        
        return trip_details
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get trip error: {str(e)}")
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
