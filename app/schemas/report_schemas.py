"""Report Schemas

Request and response schemas for report generation.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date
from enum import Enum


class ReportType(str, Enum):
    """Available report types"""
    DAILY_OPERATIONS = "daily_operations"
    MONTHLY_FLEET = "monthly_fleet"
    DRIVER_DUTY = "driver_duty"
    ROUTE_PERFORMANCE = "route_performance"
    FUEL_CONSUMPTION = "fuel_consumption"
    PLAN_HISTORY = "plan_history"


class ReportFormat(str, Enum):
    """Report output formats"""
    PDF = "pdf"
    EXCEL = "excel"
    BOTH = "both"


class ReportRequest(BaseModel):
    """Request to generate a report"""
    report_type: ReportType = Field(..., description="Type of report to generate")
    start_date: date = Field(..., description="Start date for report data")
    end_date: date = Field(..., description="End date for report data")
    depot_id: Optional[str] = Field(None, description="Filter by specific depot (optional)")
    format: ReportFormat = Field(ReportFormat.PDF, description="Output format")
    include_charts: bool = Field(True, description="Include charts and visualizations")
    include_summary: bool = Field(True, description="Include executive summary")
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_type": "daily_operations",
                "start_date": "2024-02-01",
                "end_date": "2024-02-28",
                "depot_id": "DEPOT_BHSR",
                "format": "pdf",
                "include_charts": True,
                "include_summary": True
            }
        }


class ReportFile(BaseModel):
    """Generated report file information"""
    filename: str = Field(..., description="Generated filename")
    format: str = Field(..., description="File format (pdf/excel)")
    size_bytes: int = Field(..., description="File size in bytes")
    download_url: str = Field(..., description="URL to download the file")


class ReportResponse(BaseModel):
    """Response after generating a report"""
    success: bool = Field(True, description="Whether report generation succeeded")
    report_id: str = Field(..., description="Unique report identifier")
    report_type: str = Field(..., description="Type of report generated")
    generated_at: str = Field(..., description="ISO 8601 timestamp")
    files: List[ReportFile] = Field(..., description="Generated report files")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "report_id": "RPT_20240225_001",
                "report_type": "daily_operations",
                "generated_at": "2024-02-25T10:30:00Z",
                "files": [
                    {
                        "filename": "daily_operations_2024-02-01_to_2024-02-28.pdf",
                        "format": "pdf",
                        "size_bytes": 524288,
                        "download_url": "/api/reports/download/RPT_20240225_001.pdf"
                    }
                ]
            }
        }


class ReportListItem(BaseModel):
    """Summary information for a report in the list"""
    report_id: str = Field(..., description="Unique report identifier")
    report_type: str = Field(..., description="Type of report")
    report_name: str = Field(..., description="Human-readable report name")
    generated_at: str = Field(..., description="ISO 8601 timestamp")
    start_date: str = Field(..., description="Report start date")
    end_date: str = Field(..., description="Report end date")
    depot_id: Optional[str] = Field(None, description="Depot filter (if any)")
    files: List[ReportFile] = Field(..., description="Available files")


class ReportListResponse(BaseModel):
    """Response for listing reports"""
    success: bool = Field(True, description="Whether request succeeded")
    reports: List[ReportListItem] = Field(..., description="List of reports")
    total: int = Field(..., description="Total number of reports")
    limit: int = Field(..., description="Results limit")
    offset: int = Field(..., description="Results offset")
