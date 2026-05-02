"""add ghost bus suppression tables

Revision ID: 006
Revises: 005
Create Date: 2026-05-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Create passenger_counts table
    op.create_table(
        'passenger_counts',
        sa.Column('count_id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.String(50), nullable=False),
        sa.Column('route_id', sa.String(50), nullable=False),
        sa.Column('vehicle_id', sa.String(50), nullable=True),
        sa.Column('driver_id', sa.String(50), nullable=True),
        
        # Count details
        sa.Column('passenger_count', sa.Integer(), nullable=False),
        sa.Column('boarding_count', sa.Integer(), nullable=True),
        sa.Column('alighting_count', sa.Integer(), nullable=True),
        
        # Timing
        sa.Column('trip_date', sa.Date(), nullable=False),
        sa.Column('trip_time', sa.Time(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        
        # Source
        sa.Column('source', sa.String(20), nullable=False),  # manual, automatic, estimated
        sa.Column('recorded_by', sa.String(50), nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        
        sa.PrimaryKeyConstraint('count_id')
    )
    
    # Create indexes for passenger_counts
    op.create_index('idx_passenger_counts_trip', 'passenger_counts', ['trip_id'])
    op.create_index('idx_passenger_counts_route', 'passenger_counts', ['route_id'])
    op.create_index('idx_passenger_counts_date', 'passenger_counts', ['trip_date'])
    op.create_index('idx_passenger_counts_route_date', 'passenger_counts', ['route_id', 'trip_date'])
    
    # Create trip_suppressions table
    op.create_table(
        'trip_suppressions',
        sa.Column('suppression_id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.String(50), nullable=False),
        sa.Column('route_id', sa.String(50), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('scheduled_time', sa.Time(), nullable=False),
        
        # Suppression details
        sa.Column('suppression_reason', sa.Text(), nullable=False),
        sa.Column('avg_passenger_count', sa.Numeric(5, 2), nullable=True),
        sa.Column('historical_days_analyzed', sa.Integer(), nullable=True),
        
        # Status
        sa.Column('status', sa.String(20), nullable=False),  # pending, approved, rejected, executed
        
        # Recommendation
        sa.Column('recommended_by', sa.String(50), nullable=True),  # system or supervisor_id
        sa.Column('recommended_at', sa.DateTime(), nullable=True),
        
        # Approval
        sa.Column('approved_by', sa.String(50), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        
        # Rejection
        sa.Column('rejected_by', sa.String(50), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        
        # Execution
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('vehicle_freed', sa.String(50), nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        
        sa.PrimaryKeyConstraint('suppression_id')
    )
    
    # Create indexes for trip_suppressions
    op.create_index('idx_trip_suppressions_trip', 'trip_suppressions', ['trip_id'])
    op.create_index('idx_trip_suppressions_route', 'trip_suppressions', ['route_id'])
    op.create_index('idx_trip_suppressions_status', 'trip_suppressions', ['status'])
    op.create_index('idx_trip_suppressions_date', 'trip_suppressions', ['scheduled_date'])
    op.create_index('idx_trip_suppressions_route_date', 'trip_suppressions', ['route_id', 'scheduled_date'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_trip_suppressions_route_date', 'trip_suppressions')
    op.drop_index('idx_trip_suppressions_date', 'trip_suppressions')
    op.drop_index('idx_trip_suppressions_status', 'trip_suppressions')
    op.drop_index('idx_trip_suppressions_route', 'trip_suppressions')
    op.drop_index('idx_trip_suppressions_trip', 'trip_suppressions')
    
    op.drop_index('idx_passenger_counts_route_date', 'passenger_counts')
    op.drop_index('idx_passenger_counts_date', 'passenger_counts')
    op.drop_index('idx_passenger_counts_route', 'passenger_counts')
    op.drop_index('idx_passenger_counts_trip', 'passenger_counts')
    
    # Drop tables
    op.drop_table('trip_suppressions')
    op.drop_table('passenger_counts')
