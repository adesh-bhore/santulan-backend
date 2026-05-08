"""Unscheduled Trip Management Service for Surge Drivers"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.drt.models import UnscheduledTrip
from app.models.base_models import Route, Stop, Vehicle, Driver


class UnscheduledTripService:
    """Service for managing unscheduled trip operations (surge trips)"""
    
    @staticmethod
    def start_unscheduled_trip(
        db: Session,
        unscheduled_trip_id: int,
        driver_id: str,
        actual_start_time: datetime,
        location: dict
    ) -> dict:
        """Start an unscheduled trip"""
        
        # Get unscheduled trip
        trip = db.query(UnscheduledTrip).filter(
            UnscheduledTrip.unscheduled_trip_id == unscheduled_trip_id
        ).first()
        
        if not trip:
            raise ValueError("TRIP_NOT_FOUND")
        
        # Verify driver
        if trip.driver_id != driver_id:
            raise ValueError("UNAUTHORIZED")
        
        if trip.status == "active":
            raise ValueError("TRIP_ALREADY_STARTED")
        
        if trip.status == "completed":
            raise ValueError("TRIP_ALREADY_COMPLETED")
        
        # Update trip
        trip.status = "active"
        trip.actual_start_time = actual_start_time
        trip.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(trip)
        
        return {
            "success": True,
            "trip": {
                "id": f"unscheduled-{trip.unscheduled_trip_id}",
                "tripNumber": 1000 + trip.unscheduled_trip_id,
                "status": trip.status,
                "actualStartTime": trip.actual_start_time.isoformat() if trip.actual_start_time else None
            },
            "message": "Surge trip started successfully"
        }
    
    @staticmethod
    def end_unscheduled_trip(
        db: Session,
        unscheduled_trip_id: int,
        driver_id: str,
        actual_end_time: datetime,
        location: dict,
        passenger_count: int,
        notes: Optional[str] = None
    ) -> dict:
        """End an unscheduled trip"""
        
        # Get unscheduled trip
        trip = db.query(UnscheduledTrip).filter(
            UnscheduledTrip.unscheduled_trip_id == unscheduled_trip_id
        ).first()
        
        if not trip:
            raise ValueError("TRIP_NOT_FOUND")
        
        # Verify driver
        if trip.driver_id != driver_id:
            raise ValueError("UNAUTHORIZED")
        
        if trip.status != "active":
            raise ValueError("TRIP_NOT_STARTED")
        
        # Update trip
        trip.status = "completed"
        trip.actual_end_time = actual_end_time
        trip.passenger_count = passenger_count
        trip.notes = notes
        trip.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(trip)
        
        # Record passenger count for ghost bus analysis
        try:
            from app.drt.passenger_count import PassengerCountService
            count_service = PassengerCountService(db)
            count_service.record_count(
                trip_id=f"unscheduled-{trip.unscheduled_trip_id}",
                route_id=trip.route_id,
                passenger_count=passenger_count,
                trip_date=actual_end_time.date(),
                trip_time=trip.scheduled_start_time.time(),
                source="automatic",
                vehicle_id=trip.vehicle_id,
                driver_id=trip.driver_id,
                recorded_by=trip.driver_id
            )
        except Exception as e:
            # Log error but don't fail the trip completion
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to record passenger count for unscheduled trip {unscheduled_trip_id}: {e}")
        
        return {
            "success": True,
            "trip": {
                "id": f"unscheduled-{trip.unscheduled_trip_id}",
                "tripNumber": 1000 + trip.unscheduled_trip_id,
                "status": trip.status,
                "actualStartTime": trip.actual_start_time.isoformat() if trip.actual_start_time else None,
                "actualEndTime": trip.actual_end_time.isoformat() if trip.actual_end_time else None,
                "passengerCount": trip.passenger_count
            },
            "duty": {
                "completedTrips": 1,  # Surge drivers typically have 1 trip
                "totalTrips": 1
            },
            "message": "Surge trip completed successfully"
        }
    
    @staticmethod
    def get_unscheduled_trip_details(
        db: Session,
        unscheduled_trip_id: int,
        driver_id: str
    ) -> Optional[dict]:
        """Get details of a specific unscheduled trip"""
        
        # Get unscheduled trip
        trip = db.query(UnscheduledTrip).filter(
            UnscheduledTrip.unscheduled_trip_id == unscheduled_trip_id
        ).first()
        
        if not trip:
            return None
        
        # Verify driver
        if trip.driver_id != driver_id:
            return None
        
        # Get route
        route = db.query(Route).filter(Route.route_id == trip.route_id).first()
        
        # Get stops
        start_stop = db.query(Stop).filter(Stop.stop_id == trip.start_stop_id).first()
        end_stop = db.query(Stop).filter(Stop.stop_id == trip.end_stop_id).first()
        
        # Get vehicle
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == trip.vehicle_id).first()
        
        return {
            "id": f"unscheduled-{trip.unscheduled_trip_id}",
            "tripNumber": 1000 + trip.unscheduled_trip_id,
            "routeNumber": trip.route_id,
            "startPoint": start_stop.stop_name if start_stop else trip.start_stop_id,
            "endPoint": end_stop.stop_name if end_stop else trip.end_stop_id,
            "scheduledStartTime": trip.scheduled_start_time.strftime("%H:%M"),
            "scheduledEndTime": trip.scheduled_end_time.strftime("%H:%M") if trip.scheduled_end_time else "N/A",
            "actualStartTime": trip.actual_start_time.strftime("%H:%M:%S") if trip.actual_start_time else None,
            "actualEndTime": trip.actual_end_time.strftime("%H:%M:%S") if trip.actual_end_time else None,
            "status": trip.status,
            "vehicleNumber": vehicle.vehicle_id if vehicle else "N/A",
            "passengerCount": trip.passenger_count or 0,
            "fareCollected": 0.0  # Unscheduled trips don't track fare
        }
