"""Ghost Bus Suppression Service

Analyzes historical passenger counts and recommends trip suppressions
for consistently low-demand trips.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict
import logging

from app.drt.models import PassengerCount, TripSuppression
from app.models.base_models import Route

logger = logging.getLogger(__name__)


class GhostBusService:
    """Service for ghost bus suppression logic"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_historical_demand(
        self,
        route_id: str,
        days: int = 30
    ) -> Dict:
        """
        Analyze historical passenger counts for a route
        
        Args:
            route_id: Route ID to analyze
            days: Number of days to analyze (default: 30)
            
        Returns:
            Dictionary with analysis results
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get all passenger counts for route
            counts = self.db.query(PassengerCount).filter(
                and_(
                    PassengerCount.route_id == route_id,
                    PassengerCount.trip_date >= cutoff_date
                )
            ).all()
            
            if not counts:
                return {
                    'route_id': route_id,
                    'days_analyzed': days,
                    'total_trips': 0,
                    'avg_passenger_count': 0,
                    'min_passenger_count': 0,
                    'max_passenger_count': 0,
                    'low_demand_trips': 0
                }
            
            passenger_counts = [c.passenger_count for c in counts]
            
            return {
                'route_id': route_id,
                'days_analyzed': days,
                'total_trips': len(counts),
                'avg_passenger_count': sum(passenger_counts) / len(passenger_counts),
                'min_passenger_count': min(passenger_counts),
                'max_passenger_count': max(passenger_counts),
                'low_demand_trips': len([c for c in passenger_counts if c < 5])
            }
            
        except Exception as e:
            logger.error(f"Error analyzing historical demand for route {route_id}: {e}")
            raise
    
    def identify_low_demand_trips(
        self,
        threshold: int = 5,
        days: int = 30,
        min_occurrences: int = 3
    ) -> List[Dict]:
        """
        Identify trips with consistently low demand
        
        Args:
            threshold: Passenger count threshold (default: 5)
            days: Number of days to analyze (default: 30)
            min_occurrences: Minimum occurrences to flag (default: 3)
            
        Returns:
            List of low-demand trip patterns
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Query to find trips with low passenger counts
            low_demand_query = self.db.query(
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
                func.count(PassengerCount.count_id) >= min_occurrences
            ).all()
            
            results = []
            for row in low_demand_query:
                results.append({
                    'route_id': row.route_id,
                    'trip_time': row.trip_time,
                    'avg_passenger_count': float(row.avg_count),
                    'occurrences': row.occurrences,
                    'days_analyzed': days
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error identifying low demand trips: {e}")
            raise
    
    def recommend_suppression(
        self,
        trip_id: str,
        route_id: str,
        scheduled_date: date,
        scheduled_time: time,
        reason: str,
        avg_passenger_count: Optional[float] = None,
        historical_days_analyzed: Optional[int] = None,
        recommended_by: str = 'system'
    ) -> TripSuppression:
        """
        Create a suppression recommendation
        
        Args:
            trip_id: Trip ID to suppress
            route_id: Route ID
            scheduled_date: Scheduled date
            scheduled_time: Scheduled time
            reason: Suppression reason
            avg_passenger_count: Average passenger count
            historical_days_analyzed: Days analyzed
            recommended_by: Who recommended (default: 'system')
            
        Returns:
            Created TripSuppression object
        """
        try:
            # Check if suppression already exists
            existing = self.db.query(TripSuppression).filter(
                and_(
                    TripSuppression.trip_id == trip_id,
                    TripSuppression.scheduled_date == scheduled_date,
                    TripSuppression.status.in_(['pending', 'approved'])
                )
            ).first()
            
            if existing:
                logger.warning(f"Suppression already exists for trip {trip_id} on {scheduled_date}")
                return existing
            
            # Create new suppression
            suppression = TripSuppression(
                trip_id=trip_id,
                route_id=route_id,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                suppression_reason=reason,
                avg_passenger_count=avg_passenger_count,
                historical_days_analyzed=historical_days_analyzed,
                status='pending',
                recommended_by=recommended_by,
                recommended_at=datetime.now()
            )
            
            self.db.add(suppression)
            self.db.commit()
            self.db.refresh(suppression)
            
            logger.info(f"Created suppression recommendation {suppression.suppression_id} for trip {trip_id}")
            return suppression
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating suppression recommendation: {e}")
            raise
    
    # Alias for compatibility
    def create_suppression_recommendation(self, *args, **kwargs):
        """Alias for recommend_suppression"""
        return self.recommend_suppression(*args, **kwargs)
    
    def approve_suppression(
        self,
        suppression_id: int,
        supervisor_id: str,
        notes: Optional[str] = None
    ) -> TripSuppression:
        """
        Approve a suppression recommendation
        
        Args:
            suppression_id: Suppression ID
            supervisor_id: Supervisor ID
            notes: Optional notes
            
        Returns:
            Updated TripSuppression object
        """
        try:
            suppression = self.db.query(TripSuppression).filter(
                TripSuppression.suppression_id == suppression_id
            ).first()
            
            if not suppression:
                raise ValueError(f"Suppression {suppression_id} not found")
            
            if suppression.status != 'pending':
                raise ValueError(f"Suppression {suppression_id} is not pending (status: {suppression.status})")
            
            # Update suppression
            suppression.status = 'approved'
            suppression.approved_by = supervisor_id
            suppression.approved_at = datetime.now()
            suppression.updated_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(suppression)
            
            logger.info(f"Approved suppression {suppression_id} by supervisor {supervisor_id}")
            return suppression
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error approving suppression: {e}")
            raise
    
    def reject_suppression(
        self,
        suppression_id: int,
        supervisor_id: str,
        reason: str
    ) -> TripSuppression:
        """
        Reject a suppression recommendation
        
        Args:
            suppression_id: Suppression ID
            supervisor_id: Supervisor ID
            reason: Rejection reason
            
        Returns:
            Updated TripSuppression object
        """
        try:
            suppression = self.db.query(TripSuppression).filter(
                TripSuppression.suppression_id == suppression_id
            ).first()
            
            if not suppression:
                raise ValueError(f"Suppression {suppression_id} not found")
            
            if suppression.status != 'pending':
                raise ValueError(f"Suppression {suppression_id} is not pending (status: {suppression.status})")
            
            # Update suppression
            suppression.status = 'rejected'
            suppression.rejected_by = supervisor_id
            suppression.rejected_at = datetime.now()
            suppression.rejection_reason = reason
            suppression.updated_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(suppression)
            
            logger.info(f"Rejected suppression {suppression_id} by supervisor {supervisor_id}")
            return suppression
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error rejecting suppression: {e}")
            raise
    
    def execute_suppression(
        self,
        suppression_id: int,
        vehicle_freed: Optional[str] = None
    ) -> TripSuppression:
        """
        Execute an approved suppression
        
        Args:
            suppression_id: Suppression ID
            vehicle_freed: Vehicle ID that was freed
            
        Returns:
            Updated TripSuppression object
        """
        try:
            suppression = self.db.query(TripSuppression).filter(
                TripSuppression.suppression_id == suppression_id
            ).first()
            
            if not suppression:
                raise ValueError(f"Suppression {suppression_id} not found")
            
            if suppression.status != 'approved':
                raise ValueError(f"Suppression {suppression_id} is not approved (status: {suppression.status})")
            
            # Update suppression
            suppression.status = 'executed'
            suppression.executed_at = datetime.now()
            suppression.vehicle_freed = vehicle_freed
            suppression.updated_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(suppression)
            
            logger.info(f"Executed suppression {suppression_id}")
            return suppression
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error executing suppression: {e}")
            raise
    
    def get_pending_suppressions(
        self,
        route_id: Optional[str] = None
    ) -> List[TripSuppression]:
        """
        Get all pending suppressions
        
        Args:
            route_id: Optional route filter
            
        Returns:
            List of pending suppressions
        """
        try:
            query = self.db.query(TripSuppression).filter(
                TripSuppression.status == 'pending'
            )
            
            if route_id:
                query = query.filter(TripSuppression.route_id == route_id)
            
            return query.order_by(TripSuppression.scheduled_date, TripSuppression.scheduled_time).all()
            
        except Exception as e:
            logger.error(f"Error getting pending suppressions: {e}")
            raise
    
    def get_suppression_history(
        self,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[TripSuppression]:
        """
        Get suppression history
        
        Args:
            limit: Maximum number of records
            status: Optional status filter
            
        Returns:
            List of suppressions
        """
        try:
            query = self.db.query(TripSuppression)
            
            if status:
                query = query.filter(TripSuppression.status == status)
            
            return query.order_by(TripSuppression.created_at.desc()).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting suppression history: {e}")
            raise
    
    def get_suppression_analytics(
        self,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Get suppression analytics for date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with analytics
        """
        try:
            suppressions = self.db.query(TripSuppression).filter(
                and_(
                    TripSuppression.scheduled_date >= start_date,
                    TripSuppression.scheduled_date <= end_date
                )
            ).all()
            
            total = len(suppressions)
            approved = len([s for s in suppressions if s.status == 'approved'])
            rejected = len([s for s in suppressions if s.status == 'rejected'])
            executed = len([s for s in suppressions if s.status == 'executed'])
            
            vehicles_freed = len(set([s.vehicle_freed for s in suppressions if s.vehicle_freed]))
            
            avg_counts = [s.avg_passenger_count for s in suppressions if s.avg_passenger_count]
            avg_passenger_count = sum(avg_counts) / len(avg_counts) if avg_counts else 0
            
            return {
                'total_suppressions': total,
                'approved_suppressions': approved,
                'rejected_suppressions': rejected,
                'executed_suppressions': executed,
                'approval_rate': (approved / total * 100) if total > 0 else 0,
                'vehicles_freed': vehicles_freed,
                'avg_passenger_count': avg_passenger_count,
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting suppression analytics: {e}")
            raise
