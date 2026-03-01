"""Report Routes

API endpoints for report generation and management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database.db import get_db
from app.services.report_service import ReportService
from app.schemas.report_schemas import (
    ReportRequest, ReportResponse, ReportListResponse
)
from app.schemas.error_schemas import ErrorResponse

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "/generate",
    response_model=ReportResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Report generation failed"}
    },
    summary="Generate a report",
    description="""
    Generate a report based on the specified parameters.
    
    Available report types:
    - daily_operations: Daily operations summary
    - monthly_fleet: Monthly fleet statistics
    - driver_duty: Driver duty analysis
    - route_performance: Route performance metrics
    - fuel_consumption: Fuel consumption analysis
    - plan_history: Plan history and changes
    
    Reports can be generated in PDF, Excel, or both formats.
    """
)
async def generate_report(
    request: ReportRequest,
    db: Session = Depends(get_db)
):
    """Generate a report"""
    try:
        service = ReportService(db)
        result = service.generate_report(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get(
    "/list",
    response_model=ReportListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Failed to list reports"}
    },
    summary="List recent reports",
    description="Get a list of recently generated reports with pagination support."
)
async def list_reports(
    limit: int = 20,
    offset: int = 0,
    depot_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List recent reports"""
    try:
        service = ReportService(db)
        result = service.list_reports(limit=limit, offset=offset, depot_id=depot_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list reports: {str(e)}"
        )


@router.get(
    "/download/{report_id}",
    summary="Download a report file",
    description="Download a generated report file by its ID."
)
async def download_report(report_id: str):
    """Download a report file"""
    # In production, this would serve the actual file
    # For now, return a placeholder response
    raise HTTPException(
        status_code=501,
        detail="Report download not yet implemented. File generation is mocked."
    )
