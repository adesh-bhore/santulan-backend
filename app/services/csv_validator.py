"""CSV Validation Service

Validates CSV files for each data type before database insertion.
"""

import pandas as pd
from typing import List, Dict, Tuple, Set
from io import StringIO
from sqlalchemy.orm import Session

from app.models.base_models import Depot, Route, Stop


class ValidationResult:
    """Result of CSV validation"""
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_valid: bool = True
    
    def add_error(self, message: str):
        """Add validation error"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add validation warning"""
        self.warnings.append(message)


class CSVValidator:
    """Validates CSV files for different data types"""
    
    # Required columns for each data type
    REQUIRED_COLUMNS = {
        "depots": ["depot_id", "depot_name", "latitude", "longitude"],
        "routes": ["route_id", "route_name", "depot_id"],
        "stops": ["stop_id", "stop_name", "latitude", "longitude"],
        "vehicles": ["vehicle_id", "vehicle_type", "capacity", "depot_id"],
        "drivers": ["driver_id", "driver_name", "depot_id"],
        "timetable": ["trip_id", "route_id", "start_time", "end_time", "start_stop_id", "end_stop_id", "day_type"]
    }
    
    # Optional columns with defaults
    OPTIONAL_COLUMNS = {
        "vehicles": {"emission_factor": 2.68},
        "drivers": {"max_duty_hours": 8.0}
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_csv(self, data_type: str, csv_content: str) -> Tuple[ValidationResult, pd.DataFrame]:
        """
        Validate CSV content for a specific data type.
        
        Args:
            data_type: Type of data (depots, routes, stops, vehicles, drivers, timetable)
            csv_content: CSV file content as string
        
        Returns:
            Tuple of (ValidationResult, DataFrame)
        """
        result = ValidationResult()
        
        # Check if data type is valid
        if data_type not in self.REQUIRED_COLUMNS:
            result.add_error(f"Invalid data type: {data_type}")
            return result, pd.DataFrame()
        
        try:
            # Parse CSV
            df = pd.read_csv(StringIO(csv_content))
            
            # Check if CSV is empty
            if df.empty:
                result.add_error("CSV file is empty")
                return result, df
            
            # Validate columns
            self._validate_columns(data_type, df, result)
            if not result.is_valid:
                return result, df
            
            # Add optional columns with defaults
            if data_type in self.OPTIONAL_COLUMNS:
                for col, default_val in self.OPTIONAL_COLUMNS[data_type].items():
                    if col not in df.columns:
                        df[col] = default_val
            
            # Validate data types and values
            self._validate_data_types(data_type, df, result)
            
            # Check for duplicates
            self._check_duplicates(data_type, df, result)
            
            # Validate referential integrity
            if result.is_valid:
                self._validate_referential_integrity(data_type, df, result)
            
            return result, df
            
        except pd.errors.EmptyDataError:
            result.add_error("CSV file is empty or malformed")
            return result, pd.DataFrame()
        except pd.errors.ParserError as e:
            result.add_error(f"CSV parsing error: {str(e)}")
            return result, pd.DataFrame()
        except Exception as e:
            result.add_error(f"Unexpected error during validation: {str(e)}")
            return result, pd.DataFrame()
    
    def _validate_columns(self, data_type: str, df: pd.DataFrame, result: ValidationResult):
        """Validate that all required columns are present"""
        required = set(self.REQUIRED_COLUMNS[data_type])
        present = set(df.columns)
        missing = required - present
        
        if missing:
            result.add_error(f"Missing required columns: {', '.join(missing)}")
    
    def _validate_data_types(self, data_type: str, df: pd.DataFrame, result: ValidationResult):
        """Validate data types and value constraints"""
        
        # Check for null values in required columns
        for col in self.REQUIRED_COLUMNS[data_type]:
            if df[col].isnull().any():
                null_count = df[col].isnull().sum()
                result.add_error(f"Column '{col}' has {null_count} null values")
        
        # Type-specific validations
        if data_type == "depots":
            self._validate_depots(df, result)
        elif data_type == "routes":
            self._validate_routes(df, result)
        elif data_type == "stops":
            self._validate_stops(df, result)
        elif data_type == "vehicles":
            self._validate_vehicles(df, result)
        elif data_type == "drivers":
            self._validate_drivers(df, result)
        elif data_type == "timetable":
            self._validate_timetable(df, result)
    
    def _validate_depots(self, df: pd.DataFrame, result: ValidationResult):
        """Validate depot data"""
        # Validate latitude/longitude ranges
        if not df['latitude'].between(-90, 90).all():
            result.add_error("Latitude must be between -90 and 90")
        if not df['longitude'].between(-180, 180).all():
            result.add_error("Longitude must be between -180 and 180")
    
    def _validate_routes(self, df: pd.DataFrame, result: ValidationResult):
        """Validate route data"""
        # Check route_name is not empty
        if (df['route_name'].str.strip() == '').any():
            result.add_error("Route name cannot be empty")
    
    def _validate_stops(self, df: pd.DataFrame, result: ValidationResult):
        """Validate stop data"""
        # Validate latitude/longitude ranges
        if not df['latitude'].between(-90, 90).all():
            result.add_error("Latitude must be between -90 and 90")
        if not df['longitude'].between(-180, 180).all():
            result.add_error("Longitude must be between -180 and 180")
    
    def _validate_vehicles(self, df: pd.DataFrame, result: ValidationResult):
        """Validate vehicle data"""
        # Validate capacity is positive
        try:
            if (df['capacity'] <= 0).any():
                result.add_error("Vehicle capacity must be positive")
        except (TypeError, ValueError):
            result.add_error("Vehicle capacity must be a number")
        
        # Validate emission_factor if present
        if 'emission_factor' in df.columns:
            try:
                if (df['emission_factor'] < 0).any():
                    result.add_error("Emission factor cannot be negative")
            except (TypeError, ValueError):
                result.add_error("Emission factor must be a number")
    
    def _validate_drivers(self, df: pd.DataFrame, result: ValidationResult):
        """Validate driver data"""
        # Validate max_duty_hours if present
        if 'max_duty_hours' in df.columns:
            try:
                if (df['max_duty_hours'] <= 0).any():
                    result.add_error("Max duty hours must be positive")
                if (df['max_duty_hours'] > 24).any():
                    result.add_error("Max duty hours cannot exceed 24")
            except (TypeError, ValueError):
                result.add_error("Max duty hours must be a number")
    
    def _validate_timetable(self, df: pd.DataFrame, result: ValidationResult):
        """Validate timetable data"""
        # Validate day_type
        valid_day_types = {'weekday', 'weekend'}
        invalid_day_types = set(df['day_type'].unique()) - valid_day_types
        if invalid_day_types:
            result.add_error(f"Invalid day_type values: {', '.join(invalid_day_types)}. Must be 'weekday' or 'weekend'")
        
        # Validate time format (pandas will parse these)
        try:
            pd.to_datetime(df['start_time'], format='%H:%M:%S', errors='raise')
        except:
            try:
                pd.to_datetime(df['start_time'], format='%H:%M', errors='raise')
            except:
                result.add_error("start_time must be in HH:MM:SS or HH:MM format")
        
        try:
            pd.to_datetime(df['end_time'], format='%H:%M:%S', errors='raise')
        except:
            try:
                pd.to_datetime(df['end_time'], format='%H:%M', errors='raise')
            except:
                result.add_error("end_time must be in HH:MM:SS or HH:MM format")
    
    def _check_duplicates(self, data_type: str, df: pd.DataFrame, result: ValidationResult):
        """Check for duplicate primary keys"""
        # Get primary key column
        pk_column = {
            "depots": "depot_id",
            "routes": "route_id",
            "stops": "stop_id",
            "vehicles": "vehicle_id",
            "drivers": "driver_id",
            "timetable": "trip_id"
        }[data_type]
        
        duplicates = df[df.duplicated(subset=[pk_column], keep=False)]
        if not duplicates.empty:
            dup_ids = duplicates[pk_column].unique()
            # Convert to list of strings to handle numpy types
            dup_ids_str = [str(x) for x in dup_ids]
            result.add_error(f"Duplicate {pk_column} found: {', '.join(dup_ids_str)}")
    
    def _validate_referential_integrity(self, data_type: str, df: pd.DataFrame, result: ValidationResult):
        """Validate foreign key references"""
        
        if data_type == "routes":
            # Check depot_id exists
            depot_ids = set(str(x) for x in df['depot_id'].unique())
            existing_depots = set(d[0] for d in self.db.query(Depot.depot_id).all())
            invalid_depots = depot_ids - existing_depots
            if invalid_depots:
                result.add_error(f"Invalid depot_id references: {', '.join(sorted(invalid_depots))}")
        
        elif data_type == "vehicles":
            # Check depot_id exists
            depot_ids = set(str(x) for x in df['depot_id'].unique())
            existing_depots = set(d[0] for d in self.db.query(Depot.depot_id).all())
            invalid_depots = depot_ids - existing_depots
            if invalid_depots:
                result.add_error(f"Invalid depot_id references: {', '.join(sorted(invalid_depots))}")
        
        elif data_type == "drivers":
            # Check depot_id exists
            depot_ids = set(str(x) for x in df['depot_id'].unique())
            existing_depots = set(d[0] for d in self.db.query(Depot.depot_id).all())
            invalid_depots = depot_ids - existing_depots
            if invalid_depots:
                result.add_error(f"Invalid depot_id references: {', '.join(sorted(invalid_depots))}")
        
        elif data_type == "timetable":
            # Check route_id exists
            route_ids = set(str(x) for x in df['route_id'].unique())
            existing_routes = set(str(r[0]) for r in self.db.query(Route.route_id).all())
            invalid_routes = route_ids - existing_routes
            if invalid_routes:
                result.add_error(f"Invalid route_id references: {', '.join(sorted(invalid_routes))}")
            
            # Check stop_id exists
            start_stop_ids = set(str(x) for x in df['start_stop_id'].unique())
            end_stop_ids = set(str(x) for x in df['end_stop_id'].unique())
            all_stop_ids = start_stop_ids | end_stop_ids
            existing_stops = set(s[0] for s in self.db.query(Stop.stop_id).all())
            invalid_stops = all_stop_ids - existing_stops
            if invalid_stops:
                result.add_error(f"Invalid stop_id references: {', '.join(sorted(invalid_stops))}")
