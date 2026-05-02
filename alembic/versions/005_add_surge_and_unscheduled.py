"""Add surge events and unscheduled trips tables for DRT Phase 2

Revision ID: 005
Revises: 004
Create Date: 2026-04-30 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create surge_events table
    op.create_table(
        'surge_events',
        sa.Column('surge_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('stop_id', sa.String(50), sa.ForeignKey('stops.stop_id'), nullable=False),
        sa.Column('route_ids', JSONB, nullable=False),  # Array of route IDs serving this stop
        sa.Column('ping_ids', JSONB, nullable=False),  # Array of ping IDs in this surge
        sa.Column('ping_count', sa.Integer, nullable=False),
        sa.Column('detected_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('approved_by', sa.String(50), nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('rejected_by', sa.String(50), nullable=True),
        sa.Column('rejected_at', sa.DateTime, nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Create indexes for surge_events
    op.create_index('ix_surge_events_stop_id', 'surge_events', ['stop_id'])
    op.create_index('ix_surge_events_status', 'surge_events', ['status'])
    op.create_index('ix_surge_events_detected_at', 'surge_events', ['detected_at'])
    
    # Create unscheduled_trips table
    op.create_table(
        'unscheduled_trips',
        sa.Column('unscheduled_trip_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('surge_id', sa.Integer, sa.ForeignKey('surge_events.surge_id'), nullable=False),
        sa.Column('route_id', sa.String(50), sa.ForeignKey('routes.route_id'), nullable=False),
        sa.Column('vehicle_id', sa.String(50), sa.ForeignKey('vehicles.vehicle_id'), nullable=False),
        sa.Column('driver_id', sa.String(50), sa.ForeignKey('drivers.driver_id'), nullable=False),
        sa.Column('depot_id', sa.String(50), sa.ForeignKey('depots.depot_id'), nullable=False),
        sa.Column('start_stop_id', sa.String(50), sa.ForeignKey('stops.stop_id'), nullable=False),
        sa.Column('end_stop_id', sa.String(50), sa.ForeignKey('stops.stop_id'), nullable=False),
        sa.Column('scheduled_start_time', sa.DateTime, nullable=False),
        sa.Column('scheduled_end_time', sa.DateTime, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='scheduled'),
        sa.Column('actual_start_time', sa.DateTime, nullable=True),
        sa.Column('actual_end_time', sa.DateTime, nullable=True),
        sa.Column('passenger_count', sa.Integer, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create indexes for unscheduled_trips
    op.create_index('ix_unscheduled_trips_surge_id', 'unscheduled_trips', ['surge_id'])
    op.create_index('ix_unscheduled_trips_driver_id', 'unscheduled_trips', ['driver_id'])
    op.create_index('ix_unscheduled_trips_vehicle_id', 'unscheduled_trips', ['vehicle_id'])
    op.create_index('ix_unscheduled_trips_status', 'unscheduled_trips', ['status'])
    op.create_index('ix_unscheduled_trips_scheduled_start', 'unscheduled_trips', ['scheduled_start_time'])


def downgrade() -> None:
    op.drop_index('ix_unscheduled_trips_scheduled_start', table_name='unscheduled_trips')
    op.drop_index('ix_unscheduled_trips_status', table_name='unscheduled_trips')
    op.drop_index('ix_unscheduled_trips_vehicle_id', table_name='unscheduled_trips')
    op.drop_index('ix_unscheduled_trips_driver_id', table_name='unscheduled_trips')
    op.drop_index('ix_unscheduled_trips_surge_id', table_name='unscheduled_trips')
    op.drop_table('unscheduled_trips')
    
    op.drop_index('ix_surge_events_detected_at', table_name='surge_events')
    op.drop_index('ix_surge_events_status', table_name='surge_events')
    op.drop_index('ix_surge_events_stop_id', table_name='surge_events')
    op.drop_table('surge_events')
