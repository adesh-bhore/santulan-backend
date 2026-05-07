"""Add surge vehicle and driver flags

Revision ID: 007
Revises: 006
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_surge_vehicle column to vehicles table
    op.add_column('vehicles', 
        sa.Column('is_surge_vehicle', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Add is_surge_driver column to drivers table
    op.add_column('drivers', 
        sa.Column('is_surge_driver', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Create index for faster queries
    op.create_index('ix_vehicles_is_surge', 'vehicles', ['is_surge_vehicle'])
    op.create_index('ix_drivers_is_surge', 'drivers', ['is_surge_driver'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_drivers_is_surge', table_name='drivers')
    op.drop_index('ix_vehicles_is_surge', table_name='vehicles')
    
    # Drop columns
    op.drop_column('drivers', 'is_surge_driver')
    op.drop_column('vehicles', 'is_surge_vehicle')
