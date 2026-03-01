"""CSV Upload Service

Handles CSV file uploads with validation, truncation, and bulk insertion.
"""

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List
from datetime import datetime, time

from app.services.csv_validator import CSVValidator, ValidationResult
from app.models.base_models import Depot, Route, Stop, Vehicle, Driver, Timetable


class UploadResult:
    """Result of CSV upload operation"""
    def __init__(self, data_type: str):
        self.data_type = data_type
        self.records_inserted = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.success = False


class CSVUploadService:
    """Service for uploading CSV data to database"""
    
    # Map data types to model classes
    MODEL_MAP = {
        "depots": Depot,
        "routes": Route,
        "stops": Stop,
        "vehicles": Vehicle,
        "drivers": Driver,
        "timetable": Timetable
    }
    
    # Map data types to table names
    TABLE_MAP = {
        "depots": "depots",
        "routes": "routes",
        "stops": "stops",
        "vehicles": "vehicles",
        "drivers": "drivers",
        "timetable": "timetable"
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.validator = CSVValidator(db)
    
    def upload_csv(self, data_type: str, csv_content: str) -> UploadResult:
        """
        Upload CSV data with validation and atomic transaction.
        
        Process:
        1. Validate CSV structure and data
        2. Begin transaction
        3. Truncate target table
        4. Bulk insert validated records
        5. Commit transaction (or rollback on error)
        
        Args:
            data_type: Type of data (depots, routes, stops, vehicles, drivers, timetable)
            csv_content: CSV file content as string
        
        Returns:
            UploadResult with success status, record count, errors, and warnings
        """
        result = UploadResult(data_type)
        
        # Validate data type
        if data_type not in self.MODEL_MAP:
            result.errors.append(f"Invalid data type: {data_type}")
            return result
        
        try:
            # Step 1: Validate CSV
            validation_result, df = self.validator.validate_csv(data_type, csv_content)
            
            if not validation_result.is_valid:
                result.errors = validation_result.errors
                result.warnings = validation_result.warnings
                return result
            
            # Carry over warnings from validation
            result.warnings = validation_result.warnings
            
            # Step 2-5: Truncate and insert within transaction
            try:
                # Begin transaction (implicit with session)
                self._truncate_table(data_type)
                self._bulk_insert(data_type, df)
                
                # Commit transaction
                self.db.commit()
                
                result.records_inserted = len(df)
                result.success = True
                
                return result
                
            except Exception as e:
                # Rollback on any error
                self.db.rollback()
                result.errors.append(f"Database error during upload: {str(e)}")
                return result
        
        except Exception as e:
            result.errors.append(f"Unexpected error: {str(e)}")
            return result
    
    def _truncate_table(self, data_type: str):
        """Truncate target table"""
        table_name = self.TABLE_MAP[data_type]
        
        # Tables referenced by plan tables must use DELETE instead of TRUNCATE
        # to avoid foreign key constraint errors
        # All base data tables are referenced by plan tables, so use DELETE for all
        referenced_tables = ["depots", "routes", "stops", "vehicles", "drivers", "timetable"]
        
        if data_type in referenced_tables:
            # These are referenced by plan tables - use DELETE instead of TRUNCATE
            self.db.execute(text(f"DELETE FROM {table_name}"))
        else:
            # Fallback to TRUNCATE (though all current tables use DELETE)
            self.db.execute(text(f"TRUNCATE TABLE {table_name}"))

    
    def _bulk_insert(self, data_type: str, df: pd.DataFrame):
        """Bulk insert records from DataFrame"""
        model_class = self.MODEL_MAP[data_type]
        
        # Convert DataFrame to list of model instances
        records = []
        
        if data_type == "depots":
            records = self._df_to_depots(df)
        elif data_type == "routes":
            records = self._df_to_routes(df)
        elif data_type == "stops":
            records = self._df_to_stops(df)
        elif data_type == "vehicles":
            records = self._df_to_vehicles(df)
        elif data_type == "drivers":
            records = self._df_to_drivers(df)
        elif data_type == "timetable":
            records = self._df_to_timetable(df)
        
        # Bulk insert
        self.db.bulk_save_objects(records)
    
    def _df_to_depots(self, df: pd.DataFrame) -> List[Depot]:
        """Convert DataFrame to Depot objects"""
        return [
            Depot(
                depot_id=row['depot_id'],
                depot_name=row['depot_name'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude'])
            )
            for _, row in df.iterrows()
        ]
    
    def _df_to_routes(self, df: pd.DataFrame) -> List[Route]:
        """Convert DataFrame to Route objects"""
        return [
            Route(
                route_id=row['route_id'],
                route_name=row['route_name'],
                depot_id=row['depot_id']
            )
            for _, row in df.iterrows()
        ]
    
    def _df_to_stops(self, df: pd.DataFrame) -> List[Stop]:
        """Convert DataFrame to Stop objects"""
        return [
            Stop(
                stop_id=row['stop_id'],
                stop_name=row['stop_name'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude'])
            )
            for _, row in df.iterrows()
        ]
    
    def _df_to_vehicles(self, df: pd.DataFrame) -> List[Vehicle]:
        """Convert DataFrame to Vehicle objects"""
        return [
            Vehicle(
                vehicle_id=row['vehicle_id'],
                vehicle_type=row['vehicle_type'],
                capacity=int(row['capacity']),
                depot_id=row['depot_id'],
                emission_factor=float(row.get('emission_factor', 2.68))
            )
            for _, row in df.iterrows()
        ]
    
    def _df_to_drivers(self, df: pd.DataFrame) -> List[Driver]:
        """Convert DataFrame to Driver objects"""
        return [
            Driver(
                driver_id=row['driver_id'],
                driver_name=row['driver_name'],
                depot_id=row['depot_id'],
                max_duty_hours=float(row.get('max_duty_hours', 8.0))
            )
            for _, row in df.iterrows()
        ]
    
    def _df_to_timetable(self, df: pd.DataFrame) -> List[Timetable]:
        """Convert DataFrame to Timetable objects"""
        records = []
        for _, row in df.iterrows():
            # Parse time strings
            start_time = self._parse_time(row['start_time'])
            end_time = self._parse_time(row['end_time'])
            
            records.append(
                Timetable(
                    trip_id=row['trip_id'],
                    route_id=row['route_id'],
                    start_time=start_time,
                    end_time=end_time,
                    start_stop_id=row['start_stop_id'],
                    end_stop_id=row['end_stop_id'],
                    day_type=row['day_type']
                )
            )
        return records
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string to time object"""
        # Try HH:MM:SS format first
        try:
            dt = pd.to_datetime(time_str, format='%H:%M:%S')
            return dt.time()
        except:
            # Try HH:MM format
            try:
                dt = pd.to_datetime(time_str, format='%H:%M')
                return dt.time()
            except:
                # Fallback: let pandas infer
                dt = pd.to_datetime(time_str)
                return dt.time()
