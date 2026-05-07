"""Base Data Models (Layer A)

These models represent immutable base data that is updated only via CSV uploads.
Layer A contains: routes, stops, vehicles, drivers, depots, timetable
"""

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, DateTime, Time, Date, ForeignKey, JSON
from datetime import datetime, date, time
from typing import Optional


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


class Depot(Base):
    """Depot (bus depot/garage) base data"""
    __tablename__ = "depots"
    
    depot_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    depot_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Route(Base):
    """Route base data"""
    __tablename__ = "routes"
    
    route_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    route_name: Mapped[str] = mapped_column(String(200), nullable=False)
    depot_id: Mapped[str] = mapped_column(String(50), ForeignKey("depots.depot_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Stop(Base):
    """Stop base data"""
    __tablename__ = "stops"
    
    stop_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    stop_name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Vehicle(Base):
    """Vehicle base data"""
    __tablename__ = "vehicles"
    
    vehicle_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    depot_id: Mapped[str] = mapped_column(String(50), ForeignKey("depots.depot_id"), nullable=False)
    emission_factor: Mapped[float] = mapped_column(Numeric(10, 4), default=2.68)  # kg CO2 per km
    is_surge_vehicle: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Driver(Base):
    """Driver base data"""
    __tablename__ = "drivers"
    
    driver_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    driver_name: Mapped[str] = mapped_column(String(200), nullable=False)
    depot_id: Mapped[str] = mapped_column(String(50), ForeignKey("depots.depot_id"), nullable=False)
    max_duty_hours: Mapped[float] = mapped_column(Numeric(4, 2), default=8.0)
    
    # Authentication fields
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Profile fields
    name_marathi: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    license_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Performance metrics
    rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), default=0.0, nullable=True)
    total_trips: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    on_time_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), default=0.0, nullable=True)
    safety_score: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    
    # Status
    is_active: Mapped[Optional[bool]] = mapped_column(default=True, nullable=True)
    is_surge_driver: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Timetable(Base):
    """Timetable base data"""
    __tablename__ = "timetable"
    
    trip_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    route_id: Mapped[str] = mapped_column(String(50), ForeignKey("routes.route_id"), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    start_stop_id: Mapped[str] = mapped_column(String(50), ForeignKey("stops.stop_id"), nullable=False)
    end_stop_id: Mapped[str] = mapped_column(String(50), ForeignKey("stops.stop_id"), nullable=False)
    day_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'weekday' or 'weekend'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TripLog(Base):
    """Trip log for tracking trip status and data"""
    __tablename__ = "trip_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(String(50), ForeignKey("timetable.trip_id"), nullable=False)
    driver_id: Mapped[str] = mapped_column(String(50), ForeignKey("drivers.driver_id"), nullable=False)
    vehicle_id: Mapped[Optional[str]] = mapped_column(String(50), ForeignKey("vehicles.vehicle_id"), nullable=True)
    depot_id: Mapped[str] = mapped_column(String(50), ForeignKey("depots.depot_id"), nullable=False)
    duty_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Trip status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='scheduled')
    
    # Timing
    scheduled_start_time: Mapped[time] = mapped_column(Time, nullable=False)
    scheduled_end_time: Mapped[time] = mapped_column(Time, nullable=False)
    actual_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Location (stored as JSON)
    start_location: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    end_location: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Trip data
    passenger_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fare_collected: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
