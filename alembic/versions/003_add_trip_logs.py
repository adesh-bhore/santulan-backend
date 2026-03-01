"""Add trip logs table for trip management

Revision ID: 003
Revises: 002
Create Date: 2026-02-27 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create trip_logs table
    op.create_table(
        'trip_logs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('trip_id', sa.String(50), sa.ForeignKey('timetable.trip_id'), nullable=False),
        sa.Column('driver_id', sa.String(50), sa.ForeignKey('drivers.driver_id'), nullable=False),
        sa.Column('vehicle_id', sa.String(50), sa.ForeignKey('vehicles.vehicle_id'), nullable=True),
        sa.Column('depot_id', sa.String(50), sa.ForeignKey('depots.depot_id'), nullable=False),
        sa.Column('duty_date', sa.Date, nullable=False),
        
        # Trip status
        sa.Column('status', sa.String(20), nullable=False, server_default='scheduled'),
        
        # Timing
        sa.Column('scheduled_start_time', sa.Time, nullable=False),
        sa.Column('scheduled_end_time', sa.Time, nullable=False),
        sa.Column('actual_start_time', sa.DateTime, nullable=True),
        sa.Column('actual_end_time', sa.DateTime, nullable=True),
        sa.Column('duration_minutes', sa.Integer, nullable=True),
        
        # Location
        sa.Column('start_location', JSONB, nullable=True),
        sa.Column('end_location', JSONB, nullable=True),
        
        # Trip data
        sa.Column('passenger_count', sa.Integer, nullable=True),
        sa.Column('fare_collected', sa.Numeric(10, 2), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create indexes
    op.create_index('ix_trip_logs_trip_id', 'trip_logs', ['trip_id'])
    op.create_index('ix_trip_logs_driver_id', 'trip_logs', ['driver_id'])
    op.create_index('ix_trip_logs_duty_date', 'trip_logs', ['duty_date'])
    op.create_index('ix_trip_logs_status', 'trip_logs', ['status'])
    
    # Create unique constraint for trip_id + duty_date
    op.create_unique_constraint('uq_trip_logs_trip_duty', 'trip_logs', ['trip_id', 'duty_date'])


def downgrade() -> None:
    op.drop_index('ix_trip_logs_status', table_name='trip_logs')
    op.drop_index('ix_trip_logs_duty_date', table_name='trip_logs')
    op.drop_index('ix_trip_logs_driver_id', table_name='trip_logs')
    op.drop_index('ix_trip_logs_trip_id', table_name='trip_logs')
    op.drop_table('trip_logs')
