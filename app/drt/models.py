"""DRT Data Models

These models are specific to the DRT Ping Schedule feature.
They extend the base models but are kept separate for isolation.
"""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric, DateTime, Boolean, ForeignKey, JSON
from datetime import datetime
from typing import Optional

from app.models.base_models import Base


class Commuter(Base):
    """Commuter registration for DRT ping system"""
    __tablename__ = "commuters"
    
    commuter_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    total_pings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CommuterPing(Base):
    """Commuter ping for demand-responsive transit"""
    __tablename__ = "commuter_pings"
    
    ping_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commuter_id: Mapped[str] = mapped_column(String(50), ForeignKey("commuters.commuter_id"), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    detected_stop_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("stops.stop_id"), nullable=True, index=True)
    distance_to_stop_m: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    ping_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default='pending', nullable=False, index=True)
    surge_event_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    ping_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SurgeEvent(Base):
    """Surge event detected by clustering algorithm"""
    __tablename__ = "surge_events"
    
    surge_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stop_id: Mapped[str] = mapped_column(String(50), ForeignKey("stops.stop_id"), nullable=False, index=True)
    route_ids: Mapped[dict] = mapped_column(JSON, nullable=False)  # List of route IDs
    ping_ids: Mapped[dict] = mapped_column(JSON, nullable=False)  # List of ping IDs
    ping_count: Mapped[int] = mapped_column(Integer, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default='pending', nullable=False, index=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejected_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UnscheduledTrip(Base):
    """Unscheduled trip created from approved surge event"""
    __tablename__ = "unscheduled_trips"
    
    unscheduled_trip_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    surge_id: Mapped[int] = mapped_column(Integer, ForeignKey("surge_events.surge_id"), nullable=False, index=True)
    route_id: Mapped[str] = mapped_column(String(50), ForeignKey("routes.route_id"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(50), ForeignKey("vehicles.vehicle_id"), nullable=False, index=True)
    driver_id: Mapped[str] = mapped_column(String(50), ForeignKey("drivers.driver_id"), nullable=False, index=True)
    depot_id: Mapped[str] = mapped_column(String(50), ForeignKey("depots.depot_id"), nullable=False)
    start_stop_id: Mapped[str] = mapped_column(String(50), ForeignKey("stops.stop_id"), nullable=False)
    end_stop_id: Mapped[str] = mapped_column(String(50), ForeignKey("stops.stop_id"), nullable=False)
    scheduled_start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    scheduled_end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='scheduled', nullable=False, index=True)
    actual_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    passenger_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Phase 3: Ghost Bus Suppression Models

class PassengerCount(Base):
    """Passenger count records for historical demand analysis"""
    __tablename__ = "passenger_counts"
    
    count_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    route_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    driver_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Count details
    passenger_count: Mapped[int] = mapped_column(Integer, nullable=False)
    boarding_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    alighting_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timing
    trip_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    trip_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Source
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # manual, automatic, estimated
    recorded_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TripSuppression(Base):
    """Trip suppression recommendations and execution records"""
    __tablename__ = "trip_suppressions"
    
    suppression_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    route_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Suppression details
    suppression_reason: Mapped[str] = mapped_column(String, nullable=False)
    avg_passenger_count: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    historical_days_analyzed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # pending, approved, rejected, executed
    
    # Recommendation
    recommended_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # system or supervisor_id
    recommended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Approval
    approved_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Rejection
    rejected_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Execution
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    vehicle_freed: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
