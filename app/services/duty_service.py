"""Duty Management Service for Driver App"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.base_models import Driver, Depot, Timetable, Route, Stop, Vehicle, TripLog
from app.models.plan_models import CurrentDriverAssignment, CurrentVehicleAssignment
from app.services.trip_service import TripService


class DutyService:
    """Service for managing driver duty assignments"""
    
    @staticmethod
    def get_today_duty(db: Session, driver_id: str) -> Optional[dict]:
        """Get today's duty assignment and schedule for a driver
        
        For surge drivers: Returns ONLY unscheduled trips (surge trips)
        For regular drivers: Returns regular scheduled trips + unscheduled trips (if any)
        """
        
        # Get driver information
        driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if not driver:
            return None
        
        duty_date = date.today()
        
        # Check if this is a surge driver
        is_surge_driver = getattr(driver, 'is_surge_driver', False)
        
        # For surge drivers, ONLY return unscheduled trips
        if is_surge_driver:
            unscheduled_trips = DutyService.get_unscheduled_trips_for_driver(db, driver_id, duty_date)
            
            if not unscheduled_trips:
                return None  # No surge duty assigned
            
            # Get depot information from first unscheduled trip
            from app.drt.models import UnscheduledTrip
            first_trip = db.query(UnscheduledTrip).filter(
                and_(
                    UnscheduledTrip.driver_id == driver_id,
                    UnscheduledTrip.scheduled_start_time >= datetime.combine(duty_date, datetime.min.time()),
                    UnscheduledTrip.scheduled_start_time < datetime.combine(duty_date, datetime.max.time())
                )
            ).first()
            
            depot = None
            vehicle_number = "N/A"
            if first_trip:
                depot = db.query(Depot).filter(Depot.depot_id == first_trip.depot_id).first()
                vehicle_number = first_trip.vehicle_id
            
            # Calculate shift times from unscheduled trips
            shift_start = None
            shift_end = None
            for trip in unscheduled_trips:
                trip_start = datetime.strptime(trip["startTime"], "%H:%M").time()
                trip_end = datetime.strptime(trip["endTime"], "%H:%M").time() if trip["endTime"] != "N/A" else trip_start
                
                if shift_start is None or trip_start < shift_start:
                    shift_start = trip_start
                if shift_end is None or trip_end > shift_end:
                    shift_end = trip_end
            
            # Determine duty status
            current_time = datetime.now().time()
            if shift_end and current_time > shift_end:
                duty_status = "completed"
            elif shift_start and current_time >= shift_start:
                duty_status = "active"
            else:
                duty_status = "upcoming"
            
            # Build duty info for surge driver
            duty_info = {
                "id": f"surge-duty-{date.today().strftime('%Y%m%d')}-{driver_id}",
                "date": date.today().strftime("%Y-%m-%d"),
                "routeNumber": "SURGE",
                "vehicleNumber": vehicle_number,
                "shiftStart": shift_start.strftime("%H:%M") if shift_start else "00:00",
                "shiftEnd": shift_end.strftime("%H:%M") if shift_end else "00:00",
                "depot": depot.depot_name if depot else "N/A",
                "depotMarathi": depot.depot_name if depot else "N/A",
                "totalTrips": len(unscheduled_trips),
                "completedTrips": 0,  # TODO: Track completed unscheduled trips
                "status": duty_status
            }
            
            return {
                "duty": duty_info,
                "schedule": unscheduled_trips
            }
        
        # For regular drivers, get scheduled trips
        assignments = db.query(CurrentDriverAssignment).filter(
            CurrentDriverAssignment.driver_id == driver_id
        ).order_by(CurrentDriverAssignment.sequence_order).all()
        
        if not assignments:
            # No regular assignments, check for unscheduled trips
            unscheduled_trips = DutyService.get_unscheduled_trips_for_driver(db, driver_id, duty_date)
            if unscheduled_trips:
                # Return only unscheduled trips (edge case: regular driver assigned surge trip)
                return {
                    "duty": {
                        "id": f"duty-{date.today().strftime('%Y%m%d')}-{driver_id}",
                        "date": date.today().strftime("%Y-%m-%d"),
                        "routeNumber": "UNSCHEDULED",
                        "vehicleNumber": "N/A",
                        "shiftStart": "00:00",
                        "shiftEnd": "00:00",
                        "depot": "N/A",
                        "depotMarathi": "N/A",
                        "totalTrips": len(unscheduled_trips),
                        "completedTrips": 0,
                        "status": "upcoming"
                    },
                    "schedule": unscheduled_trips
                }
            return None  # No duty assigned
        
        # Initialize trip logs if not already created
        TripService.initialize_trip_logs(db, driver_id, duty_date)
        
        # Get depot information
        depot_id = assignments[0].depot_id
        depot = db.query(Depot).filter(Depot.depot_id == depot_id).first()
        
        # Build schedule from regular assignments
        schedule = []
        shift_start = None
        shift_end = None
        route_number = None
        vehicle_number = None
        
        for idx, assignment in enumerate(assignments):
            # Get trip details
            trip = db.query(Timetable).filter(
                Timetable.trip_id == assignment.trip_id
            ).first()
            
            if not trip:
                continue
            
            # Get route details
            route = db.query(Route).filter(Route.route_id == trip.route_id).first()
            if route and not route_number:
                route_number = trip.route_id  # Use route_id as route number
            
            # Get stop details
            start_stop = db.query(Stop).filter(Stop.stop_id == trip.start_stop_id).first()
            end_stop = db.query(Stop).filter(Stop.stop_id == trip.end_stop_id).first()
            
            # Get vehicle assignment
            vehicle_assignment = db.query(CurrentVehicleAssignment).filter(
                CurrentVehicleAssignment.depot_id == depot_id,
                CurrentVehicleAssignment.trip_id == assignment.trip_id
            ).first()
            
            if vehicle_assignment and not vehicle_number:
                vehicle = db.query(Vehicle).filter(
                    Vehicle.vehicle_id == vehicle_assignment.vehicle_id
                ).first()
                if vehicle:
                    vehicle_number = vehicle.vehicle_id
            
            # Get trip status from trip_logs (source of truth)
            trip_log = db.query(TripLog).filter(
                and_(
                    TripLog.trip_id == assignment.trip_id,
                    TripLog.duty_date == duty_date
                )
            ).first()
            
            # Use status from trip_log if exists, otherwise default to scheduled
            status = trip_log.status if trip_log else "scheduled"
            
            schedule.append({
                "id": trip.trip_id,
                "tripNumber": idx + 1,
                "startPoint": start_stop.stop_name if start_stop else trip.start_stop_id,
                "endPoint": end_stop.stop_name if end_stop else trip.end_stop_id,
                "startTime": trip.start_time.strftime("%H:%M"),
                "endTime": trip.end_time.strftime("%H:%M"),
                "status": status
            })
            
            # Track shift times
            if shift_start is None or trip.start_time < shift_start:
                shift_start = trip.start_time
            if shift_end is None or trip.end_time > shift_end:
                shift_end = trip.end_time
        
        # Get unscheduled trips for regular driver (if any)
        unscheduled_trips = DutyService.get_unscheduled_trips_for_driver(db, driver_id, duty_date)
        
        # Merge unscheduled trips into schedule
        if unscheduled_trips:
            schedule.extend(unscheduled_trips)
            
            # Update shift times if unscheduled trips extend the shift
            for trip in unscheduled_trips:
                trip_start = datetime.strptime(trip["startTime"], "%H:%M").time()
                trip_end = datetime.strptime(trip["endTime"], "%H:%M").time() if trip["endTime"] != "N/A" else trip_start
                
                if shift_start is None or trip_start < shift_start:
                    shift_start = trip_start
                if shift_end is None or trip_end > shift_end:
                    shift_end = trip_end
            
            # Sort schedule by start time
            schedule.sort(key=lambda x: x["startTime"])
        
        # Count completed trips from trip_logs
        completed_trips = db.query(TripLog).filter(
            and_(
                TripLog.driver_id == driver_id,
                TripLog.duty_date == duty_date,
                TripLog.status == "completed"
            )
        ).count()
        
        # Determine duty status
        current_time = datetime.now().time()
        if shift_end and current_time > shift_end:
            duty_status = "completed"
        elif shift_start and current_time >= shift_start:
            duty_status = "active"
        else:
            duty_status = "upcoming"
        
        # Build duty info
        duty_info = {
            "id": f"duty-{date.today().strftime('%Y%m%d')}-{driver_id}",
            "date": date.today().strftime("%Y-%m-%d"),
            "routeNumber": route_number or "N/A",
            "vehicleNumber": vehicle_number or "N/A",
            "shiftStart": shift_start.strftime("%H:%M") if shift_start else "00:00",
            "shiftEnd": shift_end.strftime("%H:%M") if shift_end else "00:00",
            "depot": depot.depot_name if depot else depot_id,
            "depotMarathi": depot.depot_name if depot else depot_id,  # TODO: Add Marathi names
            "totalTrips": len(schedule),
            "completedTrips": completed_trips,
            "status": duty_status
        }
        
        return {
            "duty": duty_info,
            "schedule": schedule
        }
    
    @staticmethod
    def get_unscheduled_trips_for_driver(db: Session, driver_id: str, duty_date: date = None) -> list:
        """
        Get unscheduled trips assigned to a driver for a specific date.
        
        This is a READ-ONLY function that queries the DRT unscheduled_trips table
        without modifying any existing data.
        
        Args:
            db: Database session
            driver_id: Driver ID
            duty_date: Date to query (default: today)
        
        Returns:
            List of unscheduled trip dictionaries
        """
        from app.drt.models import UnscheduledTrip
        from app.models.base_models import Route, Stop
        
        if duty_date is None:
            duty_date = date.today()
        
        # Query unscheduled trips for this driver on this date
        unscheduled_trips = db.query(UnscheduledTrip).filter(
            and_(
                UnscheduledTrip.driver_id == driver_id,
                UnscheduledTrip.scheduled_start_time >= datetime.combine(duty_date, datetime.min.time()),
                UnscheduledTrip.scheduled_start_time < datetime.combine(duty_date, datetime.max.time())
            )
        ).order_by(UnscheduledTrip.scheduled_start_time).all()
        
        # Format unscheduled trips
        result = []
        for trip in unscheduled_trips:
            # Get route and stop details
            route = db.query(Route).filter(Route.route_id == trip.route_id).first()
            start_stop = db.query(Stop).filter(Stop.stop_id == trip.start_stop_id).first()
            end_stop = db.query(Stop).filter(Stop.stop_id == trip.end_stop_id).first()
            
            result.append({
                "id": f"unscheduled-{trip.unscheduled_trip_id}",
                "tripNumber": 1000 + trip.unscheduled_trip_id,  # Use 1000+ range for unscheduled trips
                "startPoint": start_stop.stop_name if start_stop else trip.start_stop_id,
                "endPoint": end_stop.stop_name if end_stop else trip.end_stop_id,
                "startTime": trip.scheduled_start_time.strftime("%H:%M"),
                "endTime": trip.scheduled_end_time.strftime("%H:%M") if trip.scheduled_end_time else "N/A",
                "status": trip.status,  # Use actual status from database
                "is_unscheduled": True,  # Flag to identify unscheduled trips
                "surge_reason": f"Surge trip from {start_stop.stop_name if start_stop else trip.start_stop_id}"
            })
        
        return result
