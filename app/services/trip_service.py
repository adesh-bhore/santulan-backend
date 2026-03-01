"""Trip Management Service for Driver App"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.base_models import TripLog, Timetable, Driver, Vehicle, Route, Stop
from app.models.plan_models import CurrentDriverAssignment, CurrentVehicleAssignment


class TripService:
    """Service for managing trip operations"""
    
    @staticmethod
    def initialize_trip_logs(db: Session, driver_id: str, duty_date: date) -> None:
        """Initialize trip logs for a driver's duty if not already created"""
        
        # Get driver's assignments for today
        assignments = db.query(CurrentDriverAssignment).filter(
            CurrentDriverAssignment.driver_id == driver_id
        ).order_by(CurrentDriverAssignment.sequence_order).all()
        
        if not assignments:
            return
        
        depot_id = assignments[0].depot_id
        
        # Get vehicle assignment
        vehicle_id = None
        if assignments:
            vehicle_assignment = db.query(CurrentVehicleAssignment).filter(
                CurrentVehicleAssignment.depot_id == depot_id,
                CurrentVehicleAssignment.trip_id == assignments[0].trip_id
            ).first()
            if vehicle_assignment:
                vehicle_id = vehicle_assignment.vehicle_id
        
        # Create trip logs for each assignment if not exists
        for assignment in assignments:
            # Check if trip log already exists
            existing_log = db.query(TripLog).filter(
                and_(
                    TripLog.trip_id == assignment.trip_id,
                    TripLog.duty_date == duty_date
                )
            ).first()
            
            if existing_log:
                continue
            
            # Get trip details
            trip = db.query(Timetable).filter(
                Timetable.trip_id == assignment.trip_id
            ).first()
            
            if not trip:
                continue
            
            # Create new trip log
            trip_log = TripLog(
                trip_id=assignment.trip_id,
                driver_id=driver_id,
                vehicle_id=vehicle_id,
                depot_id=depot_id,
                duty_date=duty_date,
                status='scheduled',
                scheduled_start_time=trip.start_time,
                scheduled_end_time=trip.end_time
            )
            db.add(trip_log)
        
        db.commit()
    
    @staticmethod
    def start_trip(
        db: Session,
        trip_id: str,
        driver_id: str,
        actual_start_time: datetime,
        location: dict
    ) -> dict:
        """Start a trip"""
        
        duty_date = date.today()
        
        # Get trip log
        trip_log = db.query(TripLog).filter(
            and_(
                TripLog.trip_id == trip_id,
                TripLog.driver_id == driver_id,
                TripLog.duty_date == duty_date
            )
        ).first()
        
        if not trip_log:
            raise ValueError("TRIP_NOT_FOUND")
        
        if trip_log.status == "active":
            raise ValueError("TRIP_ALREADY_STARTED")
        
        if trip_log.status == "completed":
            raise ValueError("TRIP_ALREADY_COMPLETED")
        
        # Check if there's already an active trip
        active_trip = db.query(TripLog).filter(
            and_(
                TripLog.driver_id == driver_id,
                TripLog.duty_date == duty_date,
                TripLog.status == "active"
            )
        ).first()
        
        if active_trip:
            raise ValueError("ANOTHER_TRIP_ACTIVE")
        
        # Validate sequential order - check if previous trips are completed
        assignment = db.query(CurrentDriverAssignment).filter(
            and_(
                CurrentDriverAssignment.driver_id == driver_id,
                CurrentDriverAssignment.trip_id == trip_id
            )
        ).first()
        
        if assignment and assignment.sequence_order > 1:
            # Get previous trip
            prev_assignment = db.query(CurrentDriverAssignment).filter(
                and_(
                    CurrentDriverAssignment.driver_id == driver_id,
                    CurrentDriverAssignment.sequence_order == assignment.sequence_order - 1
                )
            ).first()
            
            if prev_assignment:
                prev_trip_log = db.query(TripLog).filter(
                    and_(
                        TripLog.trip_id == prev_assignment.trip_id,
                        TripLog.duty_date == duty_date
                    )
                ).first()
                
                if prev_trip_log and prev_trip_log.status != "completed":
                    raise ValueError("SEQUENTIAL_ORDER_VIOLATION")
        
        # Update trip log
        trip_log.status = "active"
        trip_log.actual_start_time = actual_start_time
        trip_log.start_location = location
        trip_log.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(trip_log)
        
        # Get trip number
        trip_number = assignment.sequence_order if assignment else 1
        
        return {
            "success": True,
            "trip": {
                "id": trip_log.trip_id,
                "tripNumber": trip_number,
                "status": trip_log.status,
                "actualStartTime": trip_log.actual_start_time.isoformat() if trip_log.actual_start_time else None,
                "startLocation": trip_log.start_location
            },
            "message": "Trip started successfully"
        }
    
    @staticmethod
    def end_trip(
        db: Session,
        trip_id: str,
        driver_id: str,
        actual_end_time: datetime,
        location: dict,
        passenger_count: int,
        fare_collected: float,
        notes: Optional[str] = None
    ) -> dict:
        """End a trip"""
        
        duty_date = date.today()
        
        # Get trip log
        trip_log = db.query(TripLog).filter(
            and_(
                TripLog.trip_id == trip_id,
                TripLog.driver_id == driver_id,
                TripLog.duty_date == duty_date
            )
        ).first()
        
        if not trip_log:
            raise ValueError("TRIP_NOT_FOUND")
        
        if trip_log.status != "active":
            raise ValueError("TRIP_NOT_STARTED")
        
        # Calculate duration
        duration_minutes = None
        if trip_log.actual_start_time:
            # Remove timezone info for calculation if present
            start_time = trip_log.actual_start_time.replace(tzinfo=None) if trip_log.actual_start_time.tzinfo else trip_log.actual_start_time
            end_time = actual_end_time.replace(tzinfo=None) if actual_end_time.tzinfo else actual_end_time
            duration = end_time - start_time
            duration_minutes = int(duration.total_seconds() / 60)
        
        # Update trip log
        trip_log.status = "completed"
        trip_log.actual_end_time = actual_end_time
        trip_log.end_location = location
        trip_log.duration_minutes = duration_minutes
        trip_log.passenger_count = passenger_count
        trip_log.fare_collected = fare_collected
        trip_log.notes = notes
        trip_log.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(trip_log)
        
        # Get trip number
        assignment = db.query(CurrentDriverAssignment).filter(
            and_(
                CurrentDriverAssignment.driver_id == driver_id,
                CurrentDriverAssignment.trip_id == trip_id
            )
        ).first()
        trip_number = assignment.sequence_order if assignment else 1
        
        # Count completed trips
        completed_trips = db.query(TripLog).filter(
            and_(
                TripLog.driver_id == driver_id,
                TripLog.duty_date == duty_date,
                TripLog.status == "completed"
            )
        ).count()
        
        # Count total trips
        total_trips = db.query(TripLog).filter(
            and_(
                TripLog.driver_id == driver_id,
                TripLog.duty_date == duty_date
            )
        ).count()
        
        return {
            "success": True,
            "trip": {
                "id": trip_log.trip_id,
                "tripNumber": trip_number,
                "status": trip_log.status,
                "actualStartTime": trip_log.actual_start_time.isoformat() if trip_log.actual_start_time else None,
                "actualEndTime": trip_log.actual_end_time.isoformat() if trip_log.actual_end_time else None,
                "duration": trip_log.duration_minutes,
                "passengerCount": trip_log.passenger_count,
                "fareCollected": float(trip_log.fare_collected) if trip_log.fare_collected else 0.0
            },
            "duty": {
                "completedTrips": completed_trips,
                "totalTrips": total_trips
            },
            "message": "Trip ended successfully"
        }
    
    @staticmethod
    def get_trip_details(db: Session, trip_id: str, driver_id: str) -> Optional[dict]:
        """Get details of a specific trip"""
        
        duty_date = date.today()
        
        # Get trip log
        trip_log = db.query(TripLog).filter(
            and_(
                TripLog.trip_id == trip_id,
                TripLog.driver_id == driver_id,
                TripLog.duty_date == duty_date
            )
        ).first()
        
        if not trip_log:
            return None
        
        # Get trip details
        trip = db.query(Timetable).filter(Timetable.trip_id == trip_id).first()
        if not trip:
            return None
        
        # Get route
        route = db.query(Route).filter(Route.route_id == trip.route_id).first()
        
        # Get stops
        start_stop = db.query(Stop).filter(Stop.stop_id == trip.start_stop_id).first()
        end_stop = db.query(Stop).filter(Stop.stop_id == trip.end_stop_id).first()
        
        # Get vehicle
        vehicle = None
        if trip_log.vehicle_id:
            vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == trip_log.vehicle_id).first()
        
        # Get trip number
        assignment = db.query(CurrentDriverAssignment).filter(
            and_(
                CurrentDriverAssignment.driver_id == driver_id,
                CurrentDriverAssignment.trip_id == trip_id
            )
        ).first()
        trip_number = assignment.sequence_order if assignment else 1
        
        return {
            "id": trip_log.trip_id,
            "tripNumber": trip_number,
            "routeNumber": trip.route_id,
            "startPoint": start_stop.stop_name if start_stop else trip.start_stop_id,
            "endPoint": end_stop.stop_name if end_stop else trip.end_stop_id,
            "scheduledStartTime": trip.start_time.strftime("%H:%M"),
            "scheduledEndTime": trip.end_time.strftime("%H:%M"),
            "actualStartTime": trip_log.actual_start_time.strftime("%H:%M:%S") if trip_log.actual_start_time else None,
            "actualEndTime": trip_log.actual_end_time.strftime("%H:%M:%S") if trip_log.actual_end_time else None,
            "status": trip_log.status,
            "vehicleNumber": vehicle.vehicle_id if vehicle else "N/A",
            "passengerCount": trip_log.passenger_count or 0,
            "fareCollected": float(trip_log.fare_collected) if trip_log.fare_collected else 0.0
        }
