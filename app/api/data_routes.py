"""Data Upload API Routes

Handles CSV file uploads for base data tables.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import Literal

from app.database.db import get_db
from app.services.csv_service import CSVUploadService
from app.schemas.response_schemas import UploadResponse, ErrorResponse


router = APIRouter()

# Valid data types
DataType = Literal["depots", "routes", "stops", "vehicles", "drivers", "timetable"]


@router.post(
    "/upload/{data_type}",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error or invalid data type"},
        500: {"model": ErrorResponse, "description": "Server error during upload"}
    },
    summary="Upload CSV data",
    description="Upload and validate CSV file for a specific data type. Replaces all existing data in the target table."
)
async def upload_csv(
    data_type: DataType = Path(..., description="Type of data to upload"),
    file: UploadFile = File(..., description="CSV file to upload"),
    db: Session = Depends(get_db)
):
    """
    Upload CSV file for base data.
    
    **Supported data types:**
    - `depots`: Bus depots/garages
    - `routes`: Bus routes
    - `stops`: Bus stops
    - `vehicles`: Fleet vehicles
    - `drivers`: Bus drivers (password automatically set to "test123")
    - `timetable`: Trip schedules
    
    **Process:**
    1. Validate CSV structure and data
    2. Check referential integrity
    3. Truncate target table
    4. Bulk insert validated records
    5. Return summary with errors/warnings
    
    **Important:**
    - Upload replaces ALL existing data in the target table
    - Operation is atomic (all-or-nothing)
    - Validation errors prevent any database changes
    - Plan and Active tables are never modified
    - All uploaded drivers automatically get password "test123" for immediate login
    """
    
    # Validate file is CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "InvalidFileType",
                "message": "File must be a CSV file",
                "details": {"filename": file.filename}
            }
        )
    
    try:
        # Read file content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Upload CSV using service
        upload_service = CSVUploadService(db)
        result = upload_service.upload_csv(data_type, csv_content)
        
        # Check if upload was successful
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ValidationError",
                    "message": "CSV validation failed",
                    "details": {
                        "errors": result.errors,
                        "warnings": result.warnings
                    }
                }
            )
        
        # Return success response
        return UploadResponse(
            type=result.data_type,
            records_inserted=result.records_inserted,
            errors=result.errors,
            warnings=result.warnings
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "EncodingError",
                "message": "File must be UTF-8 encoded",
                "details": {"filename": file.filename}
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ServerError",
                "message": f"Unexpected error during upload: {str(e)}",
                "details": {"data_type": data_type}
            }
        )


@router.get(
    "/types",
    summary="Get supported data types",
    description="Returns list of supported data types for CSV upload"
)
async def get_data_types():
    """
    Get list of supported data types.
    
    Returns information about each data type including required columns.
    """
    return {
        "data_types": [
            {
                "type": "depots",
                "description": "Bus depots/garages",
                "required_columns": ["depot_id", "depot_name", "latitude", "longitude"],
                "optional_columns": []
            },
            {
                "type": "routes",
                "description": "Bus routes",
                "required_columns": ["route_id", "route_name", "depot_id"],
                "optional_columns": []
            },
            {
                "type": "stops",
                "description": "Bus stops",
                "required_columns": ["stop_id", "stop_name", "latitude", "longitude"],
                "optional_columns": []
            },
            {
                "type": "vehicles",
                "description": "Fleet vehicles",
                "required_columns": ["vehicle_id", "vehicle_type", "capacity", "depot_id"],
                "optional_columns": ["emission_factor"]
            },
            {
                "type": "drivers",
                "description": "Bus drivers",
                "required_columns": ["driver_id", "driver_name", "depot_id"],
                "optional_columns": ["max_duty_hours"]
            },
            {
                "type": "timetable",
                "description": "Trip schedules",
                "required_columns": ["trip_id", "route_id", "start_time", "end_time", "start_stop_id", "end_stop_id", "day_type"],
                "optional_columns": []
            }
        ]
    }



@router.get(
    "/depots",
    summary="Get all depots",
    description="Returns list of all depots with their information"
)
async def get_depots(db: Session = Depends(get_db)):
    """
    Get list of all depots.
    
    Returns all depots from the database with their details.
    """
    from app.models.base_models import Depot
    
    depots = db.query(Depot).all()
    
    return {
        "depots": [
            {
                "depot_id": depot.depot_id,
                "depot_name": depot.depot_name,
                "latitude": float(depot.latitude),
                "longitude": float(depot.longitude)
            }
            for depot in depots
        ],
        "total": len(depots)
    }


@router.get(
    "/vehicles",
    summary="Get vehicles",
    description="Returns list of vehicles with optional filtering"
)
async def get_vehicles(
    is_surge_vehicle: bool = None,
    depot_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Get list of vehicles with optional filters.
    
    - **is_surge_vehicle**: Filter by surge vehicle flag (true/false)
    - **depot_id**: Filter by depot
    """
    from app.models.base_models import Vehicle
    from sqlalchemy import and_
    
    query = db.query(Vehicle)
    
    filters = []
    if is_surge_vehicle is not None:
        filters.append(Vehicle.is_surge_vehicle == is_surge_vehicle)
    if depot_id:
        filters.append(Vehicle.depot_id == depot_id)
    
    if filters:
        query = query.filter(and_(*filters))
    
    vehicles = query.all()
    
    return {
        "vehicles": [
            {
                "vehicle_id": v.vehicle_id,
                "vehicle_type": v.vehicle_type,
                "capacity": v.capacity,
                "depot_id": v.depot_id,
                "is_surge_vehicle": getattr(v, 'is_surge_vehicle', False)
            }
            for v in vehicles
        ],
        "total": len(vehicles)
    }


@router.get(
    "/drivers",
    summary="Get drivers",
    description="Returns list of drivers with optional filtering"
)
async def get_drivers(
    is_surge_driver: bool = None,
    depot_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Get list of drivers with optional filters.
    
    - **is_surge_driver**: Filter by surge driver flag (true/false)
    - **depot_id**: Filter by depot
    """
    from app.models.base_models import Driver
    from sqlalchemy import and_
    
    query = db.query(Driver)
    
    filters = []
    if is_surge_driver is not None:
        filters.append(Driver.is_surge_driver == is_surge_driver)
    if depot_id:
        filters.append(Driver.depot_id == depot_id)
    
    if filters:
        query = query.filter(and_(*filters))
    
    drivers = query.all()
    
    return {
        "drivers": [
            {
                "driver_id": d.driver_id,
                "driver_name": d.driver_name,
                "depot_id": d.depot_id,
                "phone": d.phone,
                "is_surge_driver": getattr(d, 'is_surge_driver', False)
            }
            for d in drivers
        ],
        "total": len(drivers)
    }
