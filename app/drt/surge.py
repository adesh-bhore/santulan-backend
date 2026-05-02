"""Surge Management Service for DRT

Handles surge approval, rejection, and querying.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import logging

from app.drt.models import SurgeEvent, UnscheduledTrip, CommuterPing, Commuter
from app.models.base_models import Stop, Route, Vehicle, Driver
from app.config import settings

logger = logging.getLogger(__name__)


class SurgeService:
    """Service for managing surge events"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_active_surges(self, depot_id: Optional[str] = None) -> List[SurgeEvent]:
        """
        Get all active (pending) surge events.
        
        Args:
            depot_id: Optional depot filter
        
        Returns:
            List of pending surge events
        """
        
        query = self.db.query(SurgeEvent).filter(
            SurgeEvent.status == 'pending'
        )
        
        # TODO: Filter by depot if provided
        # Would need to join with stops and routes to get depot
        
        surges = query.order_by(desc(SurgeEvent.detected_at)).all()
        
        return surges
    
    def get_surge_detail(self, surge_id: int) -> Optional[Dict]:
        """
        Get detailed surge information including ping details.
        
        Args:
            surge_id: Surge event ID
        
        Returns:
            Dict with surge details and ping information
        """
        
        surge = self.db.query(SurgeEvent).filter(
            SurgeEvent.surge_id == surge_id
        ).first()
        
        if not surge:
            return None
        
        # Get stop info
        stop = self.db.query(Stop).filter(Stop.stop_id == surge.stop_id).first()
        
        # Get ping details
        ping_ids = surge.ping_ids if isinstance(surge.ping_ids, list) else []
        pings = self.db.query(CommuterPing).filter(
            CommuterPing.ping_id.in_(ping_ids)
        ).all()
        
        # Build ping details with commuter info
        ping_details = []
        for ping in pings:
            commuter = self.db.query(Commuter).filter(
                Commuter.commuter_id == ping.commuter_id
            ).first()
            
            ping_details.append({
                'ping_id': ping.ping_id,
                'commuter_id': ping.commuter_id,
                'commuter_name': commuter.name if commuter else 'Unknown',
                'commuter_phone': commuter.phone if commuter else 'Unknown',
                'latitude': float(ping.latitude),
                'longitude': float(ping.longitude),
                'ping_time': ping.ping_time,
                'status': ping.status
            })
        
        return {
            'surge': surge,
            'stop': stop,
            'pings': ping_details
        }
    
    def approve_surge(
        self,
        surge_id: int,
        route_id: str,
        vehicle_id: str,
        driver_id: str,
        start_stop_id: str,
        end_stop_id: str,
        scheduled_start_time: datetime,
        approved_by: str,
        notes: Optional[str] = None
    ) -> UnscheduledTrip:
        """
        Approve a surge event and create an unscheduled trip.
        
        Args:
            surge_id: Surge event ID
            route_id: Route to dispatch
            vehicle_id: Vehicle to assign
            driver_id: Driver to assign
            start_stop_id: Start stop
            end_stop_id: End stop
            scheduled_start_time: When trip should start
            approved_by: Supervisor ID who approved
            notes: Optional notes
        
        Returns:
            Created UnscheduledTrip
        
        Raises:
            ValueError: If surge not found, already processed, or validation fails
        """
        
        # Get surge
        surge = self.db.query(SurgeEvent).filter(
            SurgeEvent.surge_id == surge_id
        ).first()
        
        if not surge:
            raise ValueError(f"Surge {surge_id} not found")
        
        if surge.status != 'pending':
            raise ValueError(f"Surge {surge_id} is already {surge.status}")
        
        # Validate vehicle exists and get depot
        vehicle = self.db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
        if not vehicle:
            raise ValueError(f"Vehicle {vehicle_id} not found")
        
        # Validate driver exists and matches depot
        driver = self.db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if not driver:
            raise ValueError(f"Driver {driver_id} not found")
        
        if driver.depot_id != vehicle.depot_id:
            raise ValueError(f"Driver {driver_id} and vehicle {vehicle_id} are at different depots")
        
        # Validate route exists
        route = self.db.query(Route).filter(Route.route_id == route_id).first()
        if not route:
            raise ValueError(f"Route {route_id} not found")
        
        # Calculate end time (assume 1 hour trip)
        scheduled_end_time = scheduled_start_time + timedelta(hours=1)
        
        # Create unscheduled trip
        unscheduled_trip = UnscheduledTrip(
            surge_id=surge_id,
            route_id=route_id,
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            depot_id=vehicle.depot_id,
            start_stop_id=start_stop_id,
            end_stop_id=end_stop_id,
            scheduled_start_time=scheduled_start_time,
            scheduled_end_time=scheduled_end_time,
            status='scheduled',
            notes=notes
        )
        
        self.db.add(unscheduled_trip)
        
        # Update surge status
        surge.status = 'approved'
        surge.approved_by = approved_by
        surge.approved_at = datetime.utcnow()
        
        # Update ping statuses to 'dispatched'
        ping_ids = surge.ping_ids if isinstance(surge.ping_ids, list) else []
        self.db.query(CommuterPing).filter(
            CommuterPing.ping_id.in_(ping_ids)
        ).update({'status': 'dispatched'}, synchronize_session=False)
        
        self.db.commit()
        self.db.refresh(unscheduled_trip)
        
        logger.info(f"Surge {surge_id} approved by {approved_by}, created trip {unscheduled_trip.unscheduled_trip_id}")
        
        return unscheduled_trip
    
    def reject_surge(
        self,
        surge_id: int,
        rejected_by: str,
        reason: str
    ) -> SurgeEvent:
        """
        Reject a surge event.
        
        Args:
            surge_id: Surge event ID
            rejected_by: Supervisor ID who rejected
            reason: Reason for rejection
        
        Returns:
            Updated SurgeEvent
        
        Raises:
            ValueError: If surge not found or already processed
        """
        
        # Get surge
        surge = self.db.query(SurgeEvent).filter(
            SurgeEvent.surge_id == surge_id
        ).first()
        
        if not surge:
            raise ValueError(f"Surge {surge_id} not found")
        
        if surge.status != 'pending':
            raise ValueError(f"Surge {surge_id} is already {surge.status}")
        
        # Update surge status
        surge.status = 'rejected'
        surge.rejected_by = rejected_by
        surge.rejected_at = datetime.utcnow()
        surge.rejection_reason = reason
        
        # Update ping statuses to 'expired'
        ping_ids = surge.ping_ids if isinstance(surge.ping_ids, list) else []
        self.db.query(CommuterPing).filter(
            CommuterPing.ping_id.in_(ping_ids)
        ).update({'status': 'expired'}, synchronize_session=False)
        
        self.db.commit()
        self.db.refresh(surge)
        
        logger.info(f"Surge {surge_id} rejected by {rejected_by}: {reason}")
        
        return surge
    
    def get_surge_history(
        self,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[SurgeEvent]:
        """
        Get surge event history.
        
        Args:
            limit: Maximum number of records
            status: Optional status filter
        
        Returns:
            List of surge events
        """
        
        query = self.db.query(SurgeEvent)
        
        if status:
            query = query.filter(SurgeEvent.status == status)
        
        surges = query.order_by(desc(SurgeEvent.detected_at)).limit(limit).all()
        
        return surges
    
    def get_unscheduled_trips_for_driver(
        self,
        driver_id: str,
        date: datetime
    ) -> List[UnscheduledTrip]:
        """
        Get unscheduled trips for a driver on a specific date.
        
        Args:
            driver_id: Driver ID
            date: Date to query
        
        Returns:
            List of unscheduled trips
        """
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        trips = self.db.query(UnscheduledTrip).filter(
            and_(
                UnscheduledTrip.driver_id == driver_id,
                UnscheduledTrip.scheduled_start_time >= start_of_day,
                UnscheduledTrip.scheduled_start_time <= end_of_day
            )
        ).order_by(UnscheduledTrip.scheduled_start_time).all()
        
        return trips
