"""Commuter Service for DRT Ping System"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import math
import uuid

from app.drt.models import Commuter, CommuterPing
from app.models.base_models import Stop
from app.services.auth_service import AuthService


class CommuterService:
    """Service for managing commuters and pings"""
    
    # Configuration
    STOP_DETECTION_RADIUS_M = 500  # 500 meters radius for stop detection
    
    @staticmethod
    def register_commuter(
        db: Session,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None
    ) -> Commuter:
        """Register a new commuter"""
        
        # Check if phone already exists
        existing = db.query(Commuter).filter(Commuter.phone == phone).first()
        if existing:
            raise ValueError(f"Phone number {phone} is already registered")
        
        # Generate commuter ID
        commuter_id = f"COM_{uuid.uuid4().hex[:8].upper()}"
        
        # Hash password if provided
        password_hash = None
        if password:
            password_hash = AuthService.get_password_hash(password)
        
        # Create commuter
        commuter = Commuter(
            commuter_id=commuter_id,
            phone=phone,
            name=name,
            email=email,
            password_hash=password_hash,
            is_active=True,
            total_pings=0
        )
        
        db.add(commuter)
        db.commit()
        db.refresh(commuter)
        
        return commuter
    
    @staticmethod
    def authenticate_commuter(
        db: Session,
        phone: str,
        password: str
    ) -> Optional[Commuter]:
        """Authenticate commuter with phone and password"""
        
        commuter = db.query(Commuter).filter(
            Commuter.phone == phone,
            Commuter.is_active == True
        ).first()
        
        if not commuter:
            return None
        
        # If no password hash set, allow test password for development
        if not commuter.password_hash:
            if password == "test123":
                return commuter
            return None
        
        if not AuthService.verify_password(password, commuter.password_hash):
            return None
        
        return commuter
    
    @staticmethod
    def get_commuter(db: Session, commuter_id: str) -> Optional[Commuter]:
        """Get commuter by ID"""
        return db.query(Commuter).filter(Commuter.commuter_id == commuter_id).first()
    
    @staticmethod
    def create_ping(
        db: Session,
        commuter_id: str,
        latitude: float,
        longitude: float,
        ping_metadata: Optional[dict] = None
    ) -> Tuple[CommuterPing, Optional[Stop]]:
        """
        Create a new ping and detect nearest stop.
        
        Returns:
            Tuple of (ping, detected_stop)
        """
        
        # Verify commuter exists
        commuter = db.query(Commuter).filter(Commuter.commuter_id == commuter_id).first()
        if not commuter:
            raise ValueError(f"Commuter {commuter_id} not found")
        
        # Detect nearest stop
        detected_stop, distance_m = CommuterService._detect_nearest_stop(
            db, latitude, longitude
        )
        
        # Create ping
        ping = CommuterPing(
            commuter_id=commuter_id,
            latitude=latitude,
            longitude=longitude,
            detected_stop_id=detected_stop.stop_id if detected_stop else None,
            distance_to_stop_m=distance_m if detected_stop else None,
            ping_time=datetime.utcnow(),
            status='pending',
            ping_metadata=ping_metadata
        )
        
        db.add(ping)
        
        # Update commuter total pings
        commuter.total_pings += 1
        
        db.commit()
        db.refresh(ping)
        
        return ping, detected_stop
    
    @staticmethod
    def _detect_nearest_stop(
        db: Session,
        latitude: float,
        longitude: float
    ) -> Tuple[Optional[Stop], Optional[float]]:
        """
        Detect nearest stop within detection radius using Haversine distance.
        
        Returns:
            Tuple of (stop, distance_in_meters) or (None, None)
        """
        
        # Get all stops
        stops = db.query(Stop).all()
        
        if not stops:
            return None, None
        
        # Calculate distances to all stops
        nearest_stop = None
        min_distance = float('inf')
        
        for stop in stops:
            distance_km = CommuterService._calculate_haversine_distance(
                latitude, longitude,
                float(stop.latitude), float(stop.longitude)
            )
            distance_m = distance_km * 1000
            
            if distance_m < min_distance:
                min_distance = distance_m
                nearest_stop = stop
        
        # Check if within detection radius
        if min_distance <= CommuterService.STOP_DETECTION_RADIUS_M:
            return nearest_stop, min_distance
        
        return None, None
    
    @staticmethod
    def _calculate_haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate Haversine distance between two coordinates in km.
        Reused from TSN Builder.
        """
        
        # Earth radius in km
        R = 6371.0
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance
    
    @staticmethod
    def get_ping_history(
        db: Session,
        commuter_id: str,
        limit: int = 50
    ) -> List[CommuterPing]:
        """Get ping history for commuter"""
        
        pings = db.query(CommuterPing).filter(
            CommuterPing.commuter_id == commuter_id
        ).order_by(
            CommuterPing.ping_time.desc()
        ).limit(limit).all()
        
        return pings
    
    @staticmethod
    def get_ping_stats(db: Session, commuter_id: str) -> dict:
        """Get ping statistics for commuter"""
        
        total = db.query(func.count(CommuterPing.ping_id)).filter(
            CommuterPing.commuter_id == commuter_id
        ).scalar()
        
        pending = db.query(func.count(CommuterPing.ping_id)).filter(
            and_(
                CommuterPing.commuter_id == commuter_id,
                CommuterPing.status == 'pending'
            )
        ).scalar()
        
        processed = db.query(func.count(CommuterPing.ping_id)).filter(
            and_(
                CommuterPing.commuter_id == commuter_id,
                CommuterPing.status == 'processed'
            )
        ).scalar()
        
        surge_triggered = db.query(func.count(CommuterPing.ping_id)).filter(
            and_(
                CommuterPing.commuter_id == commuter_id,
                CommuterPing.surge_event_id.isnot(None)
            )
        ).scalar()
        
        return {
            'total_pings': total or 0,
            'pending_pings': pending or 0,
            'processed_pings': processed or 0,
            'surge_triggered_pings': surge_triggered or 0
        }
    
    @staticmethod
    def get_recent_pings(
        db: Session,
        minutes: int = 30,
        status: Optional[str] = None
    ) -> List[CommuterPing]:
        """Get recent pings within time window"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        query = db.query(CommuterPing).filter(
            CommuterPing.ping_time >= cutoff_time
        )
        
        if status:
            query = query.filter(CommuterPing.status == status)
        
        return query.order_by(CommuterPing.ping_time.desc()).all()
