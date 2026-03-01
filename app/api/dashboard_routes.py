"""Dashboard API Routes

Endpoints for dashboard metrics and statistics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services.dashboard_service import DashboardService
from app.schemas.error_schemas import ErrorResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    responses={
        500: {"model": ErrorResponse, "description": "Failed to fetch dashboard data"}
    },
    summary="Get dashboard summary",
    description="""
    Get complete dashboard summary with aggregated metrics across all depots.
    
    Returns:
    - Total vehicles and active vehicles
    - Total drivers and drivers on duty
    - Trips covered vs total trips
    - Fleet utilization percentage
    - On-time performance
    - Per-depot statistics
    - Active plans count
    """
)
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get dashboard summary with all metrics"""
    try:
        service = DashboardService(db)
        return service.get_dashboard_summary()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard summary: {str(e)}"
        )


@router.get(
    "/gauges",
    responses={
        500: {"model": ErrorResponse, "description": "Failed to fetch gauge data"}
    },
    summary="Get gauge data",
    description="""
    Get data for the four cardinal gauges in the RotaryHub.
    
    Gauges:
    - North: Fleet in Service (vehicles active vs total)
    - East: Drivers on Duty (drivers on duty vs total)
    - South: Trips Covered (trips covered vs total)
    - West: On-Time Performance (percentage)
    
    Each gauge includes current value, max value, previous value, and trend.
    """
)
async def get_gauge_data(db: Session = Depends(get_db)):
    """Get data for cardinal gauges"""
    try:
        service = DashboardService(db)
        return service.get_gauge_data()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch gauge data: {str(e)}"
        )


@router.get(
    "/depots",
    responses={
        500: {"model": ErrorResponse, "description": "Failed to fetch depot list"}
    },
    summary="Get depot list",
    description="""
    Get list of all depots with their resource counts and active plan status.
    
    For each depot returns:
    - Depot ID and name
    - Location
    - Vehicle count
    - Driver count
    - Active plan status
    - Active plan version (if any)
    """
)
async def get_depot_list(db: Session = Depends(get_db)):
    """Get list of all depots with statistics"""
    try:
        service = DashboardService(db)
        return service.get_depot_list()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch depot list: {str(e)}"
        )
