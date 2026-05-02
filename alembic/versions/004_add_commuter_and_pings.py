"""Add commuter and ping tables for DRT feature

Revision ID: 004
Revises: 003
Create Date: 2026-04-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create commuters table
    op.create_table(
        'commuters',
        sa.Column('commuter_id', sa.String(50), primary_key=True),
        sa.Column('phone', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('total_pings', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create indexes for commuters
    op.create_index('ix_commuters_phone', 'commuters', ['phone'])
    op.create_index('ix_commuters_is_active', 'commuters', ['is_active'])
    
    # Create commuter_pings table
    op.create_table(
        'commuter_pings',
        sa.Column('ping_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('commuter_id', sa.String(50), sa.ForeignKey('commuters.commuter_id'), nullable=False),
        sa.Column('latitude', sa.Numeric(10, 8), nullable=False),
        sa.Column('longitude', sa.Numeric(11, 8), nullable=False),
        sa.Column('detected_stop_id', sa.String(50), sa.ForeignKey('stops.stop_id'), nullable=True),
        sa.Column('distance_to_stop_m', sa.Numeric(10, 2), nullable=True),
        sa.Column('ping_time', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('surge_event_id', sa.Integer, nullable=True),
        sa.Column('ping_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )
    
    # Create indexes for commuter_pings
    op.create_index('ix_commuter_pings_commuter_id', 'commuter_pings', ['commuter_id'])
    op.create_index('ix_commuter_pings_detected_stop_id', 'commuter_pings', ['detected_stop_id'])
    op.create_index('ix_commuter_pings_ping_time', 'commuter_pings', ['ping_time'])
    op.create_index('ix_commuter_pings_status', 'commuter_pings', ['status'])
    op.create_index('ix_commuter_pings_surge_event_id', 'commuter_pings', ['surge_event_id'])


def downgrade() -> None:
    op.drop_index('ix_commuter_pings_surge_event_id', table_name='commuter_pings')
    op.drop_index('ix_commuter_pings_status', table_name='commuter_pings')
    op.drop_index('ix_commuter_pings_ping_time', table_name='commuter_pings')
    op.drop_index('ix_commuter_pings_detected_stop_id', table_name='commuter_pings')
    op.drop_index('ix_commuter_pings_commuter_id', table_name='commuter_pings')
    op.drop_table('commuter_pings')
    
    op.drop_index('ix_commuters_is_active', table_name='commuters')
    op.drop_index('ix_commuters_phone', table_name='commuters')
    op.drop_table('commuters')
