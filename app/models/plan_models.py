"""Plan Models (Layer B) and Active Tables Models (Layer C)

Layer B: Plan tables (immutable after creation) - plans, plan_vehicle_assignments, plan_driver_assignments
Layer C: Active tables (updated only on deployment) - current_vehicle_assignments, current_driver_assignments
"""

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from typing import Optional
import uuid

# Import Base from base_models to share metadata
from app.models.base_models import Base


# ============================================================================
# Layer B: Plan Tables (Immutable After Creation)
# ============================================================================

class Plan(Base):
    """Optimization plan with metadata and metrics"""
    __tablename__ = "plans"
    
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    depot_id: Mapped[str] = mapped_column(String(50), ForeignKey("depots.depot_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    day_type: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Optimization metrics
    fleet_size: Mapped[int] = mapped_column(Integer, nullable=False)
    total_deadhead_km: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_emissions_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    duty_variance_minutes: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    trips_covered: Mapped[int] = mapped_column(Integer, nullable=False)
    trips_total: Mapped[int] = mapped_column(Integer, nullable=False)
    solver_time_seconds: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Objective weights used for optimization
    objective_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('depot_id', 'version', name='uq_depot_version'),
        CheckConstraint("status IN ('PENDING', 'ACTIVE', 'ARCHIVED')", name='ck_plan_status'),
        Index('idx_plans_depot_status', 'depot_id', 'status'),
        Index('idx_plans_status', 'status'),
    )


class PlanVehicleAssignment(Base):
    """Vehicle-to-trip assignments for a specific plan"""
    __tablename__ = "plan_vehicle_assignments"
    
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.plan_id", ondelete="CASCADE"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(50), ForeignKey("vehicles.vehicle_id"), nullable=False)
    trip_id: Mapped[str] = mapped_column(String(50), ForeignKey("timetable.trip_id"), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    deadhead_km: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_pva_plan', 'plan_id'),
        Index('idx_pva_vehicle', 'vehicle_id'),
    )


class PlanDriverAssignment(Base):
    """Driver-to-trip assignments for a specific plan"""
    __tablename__ = "plan_driver_assignments"
    
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.plan_id", ondelete="CASCADE"), nullable=False)
    driver_id: Mapped[str] = mapped_column(String(50), ForeignKey("drivers.driver_id"), nullable=False)
    trip_id: Mapped[str] = mapped_column(String(50), ForeignKey("timetable.trip_id"), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    duty_hours: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_pda_plan', 'plan_id'),
        Index('idx_pda_driver', 'driver_id'),
    )


# ============================================================================
# Layer C: Active Tables (Updated Only on Deployment)
# ============================================================================

class CurrentVehicleAssignment(Base):
    """Currently active vehicle-to-trip assignments (deployed plan)"""
    __tablename__ = "current_vehicle_assignments"
    
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    depot_id: Mapped[str] = mapped_column(String(50), ForeignKey("depots.depot_id"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(50), ForeignKey("vehicles.vehicle_id"), nullable=False)
    trip_id: Mapped[str] = mapped_column(String(50), ForeignKey("timetable.trip_id"), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    deadhead_km: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    deployed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_cva_depot', 'depot_id'),
        Index('idx_cva_vehicle', 'vehicle_id'),
    )


class CurrentDriverAssignment(Base):
    """Currently active driver-to-trip assignments (deployed plan)"""
    __tablename__ = "current_driver_assignments"
    
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    depot_id: Mapped[str] = mapped_column(String(50), ForeignKey("depots.depot_id"), nullable=False)
    driver_id: Mapped[str] = mapped_column(String(50), ForeignKey("drivers.driver_id"), nullable=False)
    trip_id: Mapped[str] = mapped_column(String(50), ForeignKey("timetable.trip_id"), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    duty_hours: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0)
    deployed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_cda_depot', 'depot_id'),
        Index('idx_cda_driver', 'driver_id'),
    )
