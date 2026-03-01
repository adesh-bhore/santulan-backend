"""Add driver authentication fields

Revision ID: 002
Revises: 001
Create Date: 2026-02-27 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add authentication and profile fields to drivers table
    op.add_column('drivers', sa.Column('employee_id', sa.String(50), nullable=True, unique=True))
    op.add_column('drivers', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('drivers', sa.Column('name_marathi', sa.String(200), nullable=True))
    op.add_column('drivers', sa.Column('phone', sa.String(20), nullable=True))
    op.add_column('drivers', sa.Column('email', sa.String(100), nullable=True))
    op.add_column('drivers', sa.Column('license_number', sa.String(50), nullable=True))
    op.add_column('drivers', sa.Column('rating', sa.Numeric(3, 2), nullable=True, server_default='0.0'))
    op.add_column('drivers', sa.Column('total_trips', sa.Integer, nullable=True, server_default='0'))
    op.add_column('drivers', sa.Column('on_time_percent', sa.Numeric(5, 2), nullable=True, server_default='0.0'))
    op.add_column('drivers', sa.Column('safety_score', sa.Integer, nullable=True, server_default='0'))
    op.add_column('drivers', sa.Column('is_active', sa.Boolean, nullable=True, server_default='true'))
    
    # Create index on employee_id for faster lookups
    op.create_index('ix_drivers_employee_id', 'drivers', ['employee_id'])


def downgrade() -> None:
    op.drop_index('ix_drivers_employee_id', table_name='drivers')
    op.drop_column('drivers', 'is_active')
    op.drop_column('drivers', 'safety_score')
    op.drop_column('drivers', 'on_time_percent')
    op.drop_column('drivers', 'total_trips')
    op.drop_column('drivers', 'rating')
    op.drop_column('drivers', 'license_number')
    op.drop_column('drivers', 'email')
    op.drop_column('drivers', 'phone')
    op.drop_column('drivers', 'name_marathi')
    op.drop_column('drivers', 'password_hash')
    op.drop_column('drivers', 'employee_id')
