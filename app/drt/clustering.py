"""Clustering Service for DRT Surge Detection

This service runs as a background job every 5 minutes to:
1. Group pending pings by route corridor (which routes serve that stop)
2. Detect surges when ping count >= threshold (default: 50)
3. Create surge events for supervisor approval
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

from app.drt.models import CommuterPing, SurgeEvent
from app.models.base_models import Stop, Route, Timetable
from app.config import settings

logger = logging.getLogger(__name__)


class ClusteringService:
    """Service for clustering pings and detecting surges"""
    
    def __init__(self, db: Session):
        self.db = db
        self.surge_threshold = settings.drt_surge_ping_threshold
        self.ping_expiry_minutes = settings.drt_ping_expiry_minutes
        self.next_bus_gap_minutes = getattr(settings, 'drt_next_bus_gap_minutes', 15)
    
    def run_clustering_job(self) -> Dict:
        """
        Main clustering job that runs every 5 minutes.
        
        Returns:
            Dict with job statistics
        """
        logger.info("Starting clustering job...")
        
        try:
            # Get pending pings within expiry window
            pending_pings = self._get_pending_pings()
            
            if not pending_pings:
                logger.info("No pending pings to process")
                return {
                    'status': 'success',
                    'pending_pings': 0,
                    'surges_detected': 0
                }
            
            logger.info(f"Found {len(pending_pings)} pending pings")
            
            # Group pings by stop
            pings_by_stop = self._group_pings_by_stop(pending_pings)
            
            # Process each stop
            surges_created = 0
            for stop_id, pings in pings_by_stop.items():
                # Map stop to route corridors
                route_corridors = self._map_stop_to_corridors(stop_id)
                
                if not route_corridors:
                    logger.warning(f"Stop {stop_id} has no routes serving it")
                    continue
                
                # Group pings by route corridor
                for route_id in route_corridors:
                    corridor_pings = pings  # All pings at this stop are for this corridor
                    
                    if len(corridor_pings) >= self.surge_threshold:
                        # Check if next bus is coming soon
                        if self._is_next_bus_coming_soon(route_id, stop_id):
                            logger.info(f"Skipping surge for {route_id} at {stop_id} - bus coming soon")
                            continue
                        
                        # Create surge event
                        surge = self._create_surge_event(
                            stop_id=stop_id,
                            route_ids=[route_id],
                            pings=corridor_pings
                        )
                        
                        if surge:
                            surges_created += 1
                            logger.info(f"Created surge {surge.surge_id} for {route_id} at {stop_id}")
                            
                            # Broadcast surge event via WebSocket
                            self._broadcast_surge_event(surge)
            
            logger.info(f"Clustering job complete: {surges_created} surges created")
            
            return {
                'status': 'success',
                'pending_pings': len(pending_pings),
                'surges_detected': surges_created
            }
        
        except Exception as e:
            logger.error(f"Clustering job failed: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _get_pending_pings(self) -> List[CommuterPing]:
        """
        Get pending pings within 2-hour window, counting only ONE ping per unique commuter.
        This prevents spam from same commuter making multiple pings.
        """
        
        # Use 2-hour window (120 minutes) for unique commuter counting
        cutoff_time = datetime.utcnow() - timedelta(minutes=120)
        
        # Get only the LATEST ping per commuter within 2-hour window
        # Using subquery to get max ping_id per commuter
        from sqlalchemy import select
        
        subquery = (
            select(
                CommuterPing.commuter_id,
                func.max(CommuterPing.ping_id).label('max_ping_id')
            )
            .where(
                and_(
                    CommuterPing.status == 'pending',
                    CommuterPing.detected_stop_id.isnot(None),
                    CommuterPing.ping_time >= cutoff_time
                )
            )
            .group_by(CommuterPing.commuter_id)
            .subquery()
        )
        
        # Get the actual ping records for these max ping_ids
        pings = self.db.query(CommuterPing).join(
            subquery,
            and_(
                CommuterPing.commuter_id == subquery.c.commuter_id,
                CommuterPing.ping_id == subquery.c.max_ping_id
            )
        ).all()
        
        logger.info(f"Found {len(pings)} unique commuter pings within 2-hour window")
        
        return pings
    
    def _group_pings_by_stop(self, pings: List[CommuterPing]) -> Dict[str, List[CommuterPing]]:
        """Group pings by stop ID"""
        
        pings_by_stop = {}
        for ping in pings:
            stop_id = ping.detected_stop_id
            if stop_id not in pings_by_stop:
                pings_by_stop[stop_id] = []
            pings_by_stop[stop_id].append(ping)
        
        return pings_by_stop
    
    def _map_stop_to_corridors(self, stop_id: str) -> List[str]:
        """
        Map stop to route corridors (which routes serve this stop).
        
        Now supports intermediate stops via route_stops table!
        Falls back to start/end stop logic if route_stops not available.
        
        Returns:
            List of route IDs that serve this stop
        """
        
        # Try route_stops table first (for intermediate stops)
        try:
            from app.models.base_models import RouteStop
            
            routes = self.db.query(RouteStop.route_id).filter(
                RouteStop.stop_id == stop_id
            ).distinct().all()
            
            if routes:
                route_ids = [r.route_id for r in routes]
                logger.info(f"Found {len(route_ids)} routes for stop {stop_id} via route_stops (corridor clustering)")
                return route_ids
            else:
                logger.debug(f"No routes found in route_stops for stop {stop_id}, trying fallback")
        
        except Exception as e:
            logger.warning(f"route_stops table not available or error: {e}, using fallback logic")
        
        # Fallback: Find all routes that have trips starting or ending at this stop
        routes = self.db.query(Route.route_id).join(
            Timetable, Route.route_id == Timetable.route_id
        ).filter(
            (Timetable.start_stop_id == stop_id) | (Timetable.end_stop_id == stop_id)
        ).distinct().all()
        
        route_ids = [r.route_id for r in routes]
        logger.info(f"Found {len(route_ids)} routes for stop {stop_id} via timetable (start/end stops only)")
        
        return route_ids
    
    def _is_next_bus_coming_soon(self, route_id: str, stop_id: str) -> bool:
        """
        Check if next scheduled bus is coming within gap threshold.
        
        Args:
            route_id: Route ID
            stop_id: Stop ID
        
        Returns:
            True if bus coming within next_bus_gap_minutes
        """
        
        current_time = datetime.utcnow().time()
        current_day_type = 'weekday'  # TODO: Determine from current date
        
        # Find next trip on this route starting at this stop
        next_trip = self.db.query(Timetable).filter(
            and_(
                Timetable.route_id == route_id,
                Timetable.start_stop_id == stop_id,
                Timetable.day_type == current_day_type,
                Timetable.start_time >= current_time
            )
        ).order_by(Timetable.start_time).first()
        
        if not next_trip:
            return False
        
        # Calculate time difference
        from datetime import datetime as dt
        base_date = dt(2000, 1, 1)
        current_dt = dt.combine(base_date, current_time)
        next_dt = dt.combine(base_date, next_trip.start_time)
        
        time_diff_minutes = (next_dt - current_dt).total_seconds() / 60
        
        return time_diff_minutes <= self.next_bus_gap_minutes
    
    def _create_surge_event(
        self,
        stop_id: str,
        route_ids: List[str],
        pings: List[CommuterPing]
    ) -> SurgeEvent:
        """
        Create a surge event for supervisor approval.
        
        Args:
            stop_id: Stop ID where surge detected
            route_ids: List of route IDs for this corridor
            pings: List of pings in this surge
        
        Returns:
            Created SurgeEvent
        """
        
        # Check if surge already exists for this stop (idempotency)
        existing_surge = self.db.query(SurgeEvent).filter(
            and_(
                SurgeEvent.stop_id == stop_id,
                SurgeEvent.status == 'pending',
                SurgeEvent.detected_at >= datetime.utcnow() - timedelta(minutes=10)
            )
        ).first()
        
        if existing_surge:
            logger.info(f"Surge already exists for stop {stop_id}")
            return existing_surge
        
        # Create surge event
        ping_ids = [ping.ping_id for ping in pings]
        
        surge = SurgeEvent(
            stop_id=stop_id,
            route_ids=route_ids,  # Store as JSON array
            ping_ids=ping_ids,  # Store as JSON array
            ping_count=len(pings),
            detected_at=datetime.utcnow(),
            status='pending'
        )
        
        self.db.add(surge)
        
        # Update ping statuses to 'clustered'
        for ping in pings:
            ping.status = 'clustered'
            ping.surge_event_id = None  # Will be set after commit
        
        self.db.commit()
        
        # Update pings with surge_id
        for ping in pings:
            ping.surge_event_id = surge.surge_id
        
        self.db.commit()
        self.db.refresh(surge)
        
        return surge
    
    def _broadcast_surge_event(self, surge: SurgeEvent):
        """
        Broadcast surge event to connected WebSocket clients.
        
        Args:
            surge: SurgeEvent to broadcast
        """
        try:
            # Import here to avoid circular dependency
            from app.drt.websocket import surge_ws_manager
            import asyncio
            
            # Get stop name
            stop = self.db.query(Stop).filter(Stop.stop_id == surge.stop_id).first()
            
            # Prepare surge data
            surge_data = {
                'surge_id': surge.surge_id,
                'stop_id': surge.stop_id,
                'stop_name': stop.stop_name if stop else None,
                'route_ids': surge.route_ids if isinstance(surge.route_ids, list) else [],
                'ping_count': surge.ping_count,
                'detected_at': surge.detected_at.isoformat(),
                'status': surge.status
            }
            
            # Get depot_id from stop (if available)
            depot_id = stop.depot_id if stop and hasattr(stop, 'depot_id') else "ALL"
            
            # Broadcast to WebSocket clients
            # Note: This runs in a background thread, so we need to create a new event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(
                surge_ws_manager.broadcast_surge(surge_data, depot_id)
            )
            
            logger.info(f"Broadcasted surge {surge.surge_id} via WebSocket")
        
        except Exception as e:
            logger.error(f"Failed to broadcast surge event: {str(e)}", exc_info=True)
            # Don't fail the job if broadcast fails


def run_clustering_job_wrapper(db: Session):
    """Wrapper function for APScheduler"""
    service = ClusteringService(db)
    return service.run_clustering_job()
