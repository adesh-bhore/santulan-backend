"""Passenger Count Service

Records and analyzes passenger counts for trips.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict
import logging

from app.drt.models import PassengerCount

logger = logging.getLogger(__name__)


class PassengerCountService:
    """Service for passenger count management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_count(
        self,
        trip_id: str,
        route_id: str,
        passenger_count: int,
        trip_date: date,
        trip_time: time,
        source: str = 'manual',
        vehicle_id: Optional[str] = None,
        driver_id: Optional[str] = None,
        boarding_count: Optional[int] = None,
        alighting_count: Optional[int] = None,
        recorded_by: Optional[str] = None
    ) -> PassengerCount:
        """
        Record a passenger count
        
        Args:
            trip_id: Trip ID
            route_id: Route ID
            passenger_count: Total passenger count
            trip_date: Trip date
            trip_time: Trip time
            source: Source of count (manual, automatic, estimated)
            vehicle_id: Optional vehicle ID
            driver_id: Optional driver ID
            boarding_count: Optional boarding count
            alighting_count: Optional alighting count
            recorded_by: Optional recorder ID
            
        Returns:
            Created PassengerCount object
        """
        try:
            # Validate passenger count
            if passenger_count < 0:
                raise ValueError("Passenger count cannot be negative")
            
            # Create passenger count record
            count = PassengerCount(
                trip_id=trip_id,
                route_id=route_id,
                vehicle_id=vehicle_id,
                driver_id=driver_id,
                passenger_count=passenger_count,
                boarding_count=boarding_count,
                alighting_count=alighting_count,
                trip_date=trip_date,
                trip_time=trip_time,
                source=source,
                recorded_by=recorded_by,
                recorded_at=datetime.now()
            )
            
            self.db.add(count)
            self.db.commit()
            self.db.refresh(count)
            
            logger.info(f"Recorded passenger count {count.count_id} for trip {trip_id}: {passenger_count} passengers")
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording passenger count: {e}")
            raise
    
    def get_historical_counts(
        self,
        route_id: str,
        days: int = 30
    ) -> List[PassengerCount]:
        """
        Get historical passenger counts for a route
        
        Args:
            route_id: Route ID
            days: Number of days to retrieve (default: 30)
            
        Returns:
            List of PassengerCount objects
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            counts = self.db.query(PassengerCount).filter(
                and_(
                    PassengerCount.route_id == route_id,
                    PassengerCount.trip_date >= cutoff_date
                )
            ).order_by(PassengerCount.trip_date.desc()).all()
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting historical counts for route {route_id}: {e}")
            raise
    
    def calculate_average(
        self,
        route_id: str,
        trip_time: Optional[time] = None,
        days: int = 30
    ) -> float:
        """
        Calculate average passenger count
        
        Args:
            route_id: Route ID
            trip_time: Optional specific trip time
            days: Number of days to analyze (default: 30)
            
        Returns:
            Average passenger count
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            query = self.db.query(func.avg(PassengerCount.passenger_count)).filter(
                and_(
                    PassengerCount.route_id == route_id,
                    PassengerCount.trip_date >= cutoff_date
                )
            )
            
            if trip_time:
                query = query.filter(PassengerCount.trip_time == trip_time)
            
            result = query.scalar()
            return float(result) if result else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating average for route {route_id}: {e}")
            raise
    
    def get_counts_by_trip(
        self,
        trip_id: str
    ) -> List[PassengerCount]:
        """
        Get all passenger counts for a specific trip
        
        Args:
            trip_id: Trip ID
            
        Returns:
            List of PassengerCount objects
        """
        try:
            counts = self.db.query(PassengerCount).filter(
                PassengerCount.trip_id == trip_id
            ).order_by(PassengerCount.trip_date.desc()).all()
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting counts for trip {trip_id}: {e}")
            raise
    
    def get_demand_trends(
        self,
        route_id: Optional[str] = None,
        days: int = 30
    ) -> List[Dict]:
        """
        Get demand trends over time
        
        Args:
            route_id: Optional route filter
            days: Number of days to analyze (default: 30)
            
        Returns:
            List of trend data
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            query = self.db.query(
                PassengerCount.route_id,
                PassengerCount.trip_date,
                func.avg(PassengerCount.passenger_count).label('avg_count'),
                func.count(PassengerCount.count_id).label('trip_count')
            ).filter(
                PassengerCount.trip_date >= cutoff_date
            )
            
            if route_id:
                query = query.filter(PassengerCount.route_id == route_id)
            
            query = query.group_by(
                PassengerCount.route_id,
                PassengerCount.trip_date
            ).order_by(
                PassengerCount.trip_date
            )
            
            results = []
            for row in query.all():
                results.append({
                    'route_id': row.route_id,
                    'date': row.trip_date,
                    'avg_passenger_count': float(row.avg_count),
                    'trip_count': row.trip_count
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting demand trends: {e}")
            raise
    
    def get_low_demand_patterns(
        self,
        threshold: int = 5,
        days: int = 30
    ) -> List[Dict]:
        """
        Identify low-demand patterns
        
        Args:
            threshold: Passenger count threshold (default: 5)
            days: Number of days to analyze (default: 30)
            
        Returns:
            List of low-demand patterns
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            query = self.db.query(
                PassengerCount.route_id,
                PassengerCount.trip_time,
                func.avg(PassengerCount.passenger_count).label('avg_count'),
                func.count(PassengerCount.count_id).label('occurrences')
            ).filter(
                and_(
                    PassengerCount.trip_date >= cutoff_date,
                    PassengerCount.passenger_count < threshold
                )
            ).group_by(
                PassengerCount.route_id,
                PassengerCount.trip_time
            ).having(
                func.count(PassengerCount.count_id) >= 3  # At least 3 occurrences
            ).order_by(
                func.avg(PassengerCount.passenger_count)
            )
            
            results = []
            for row in query.all():
                results.append({
                    'route_id': row.route_id,
                    'trip_time': row.trip_time,
                    'avg_passenger_count': float(row.avg_count),
                    'occurrences': row.occurrences
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting low demand patterns: {e}")
            raise
