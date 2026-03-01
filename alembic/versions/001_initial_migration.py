"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables for the PMPML backend"""
    
    # Layer A: Base Data Tables
    
    # Create depots table
    op.create_table(
        'depots',
        sa.Column('depot_id', sa.String(50), primary_key=True),
        sa.Column('depot_name', sa.String(200), nullable=False),
        sa.Column('latitude', sa.Numeric(10, 8), nullable=False),
        sa.Column('longitude', sa.Numeric(11, 8), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'))
    )
    
    # Create routes table
    op.create_table(
        'routes',
        sa.Column('route_id', sa.String(50), primary_key=True),
        sa.Column('route_name', sa.String(200), nullable=False),
        sa.Column('depot_id', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['depot_id'], ['depots.depot_id'])
    )
    
    # Create stops table
    op.create_table(
        'stops',
        sa.Column('stop_id', sa.String(50), primary_key=True),
        sa.Column('stop_name', sa.String(200), nullable=False),
        sa.Column('latitude', sa.Numeric(10, 8), nullable=False),
        sa.Column('longitude', sa.Numeric(11, 8), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'))
    )
    
    # Create vehicles table
    op.create_table(
        'vehicles',
        sa.Column('vehicle_id', sa.String(50), primary_key=True),
        sa.Column('vehicle_type', sa.String(50), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('depot_id', sa.String(50), nullable=False),
        sa.Column('emission_factor', sa.Numeric(10, 4), server_default='2.68'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['depot_id'], ['depots.depot_id'])
    )
    
    # Create drivers table
    op.create_table(
        'drivers',
        sa.Column('driver_id', sa.String(50), primary_key=True),
        sa.Column('driver_name', sa.String(200), nullable=False),
        sa.Column('depot_id', sa.String(50), nullable=False),
        sa.Column('max_duty_hours', sa.Numeric(4, 2), server_default='8.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['depot_id'], ['depots.depot_id'])
    )
    
    # Create timetable table
    op.create_table(
        'timetable',
        sa.Column('trip_id', sa.String(50), primary_key=True),
        sa.Column('route_id', sa.String(50), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('start_stop_id', sa.String(50), nullable=False),
        sa.Column('end_stop_id', sa.String(50), nullable=False),
        sa.Column('day_type', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['route_id'], ['routes.route_id']),
        sa.ForeignKeyConstraint(['start_stop_id'], ['stops.stop_id']),
        sa.ForeignKeyConstraint(['end_stop_id'], ['stops.stop_id'])
    )
    
    # Layer B: Plan Tables
    
    # Create plans table
    op.create_table(
        'plans',
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('depot_id', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('day_type', sa.String(20), nullable=False),
        sa.Column('fleet_size', sa.Integer(), nullable=False),
        sa.Column('total_deadhead_km', sa.Numeric(10, 2), nullable=False),
        sa.Column('estimated_emissions_kg', sa.Numeric(10, 2), nullable=False),
        sa.Column('duty_variance_minutes', sa.Numeric(10, 2), nullable=False),
        sa.Column('trips_covered', sa.Integer(), nullable=False),
        sa.Column('trips_total', sa.Integer(), nullable=False),
        sa.Column('solver_time_seconds', sa.Numeric(10, 2), nullable=False),
        sa.Column('objective_weights', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('deployed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['depot_id'], ['depots.depot_id']),
        sa.UniqueConstraint('depot_id', 'version', name='uq_depot_version'),
        sa.CheckConstraint("status IN ('PENDING', 'ACTIVE', 'ARCHIVED')", name='ck_plan_status')
    )
    op.create_index('idx_plans_depot_status', 'plans', ['depot_id', 'status'])
    op.create_index('idx_plans_status', 'plans', ['status'])
    
    # Create plan_vehicle_assignments table
    op.create_table(
        'plan_vehicle_assignments',
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vehicle_id', sa.String(50), nullable=False),
        sa.Column('trip_id', sa.String(50), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('deadhead_km', sa.Numeric(10, 2), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.plan_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.vehicle_id']),
        sa.ForeignKeyConstraint(['trip_id'], ['timetable.trip_id'])
    )
    op.create_index('idx_pva_plan', 'plan_vehicle_assignments', ['plan_id'])
    op.create_index('idx_pva_vehicle', 'plan_vehicle_assignments', ['vehicle_id'])
    
    # Create plan_driver_assignments table
    op.create_table(
        'plan_driver_assignments',
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('driver_id', sa.String(50), nullable=False),
        sa.Column('trip_id', sa.String(50), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('duty_hours', sa.Numeric(4, 2), nullable=False),
        sa.Column('break_minutes', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.plan_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id']),
        sa.ForeignKeyConstraint(['trip_id'], ['timetable.trip_id'])
    )
    op.create_index('idx_pda_plan', 'plan_driver_assignments', ['plan_id'])
    op.create_index('idx_pda_driver', 'plan_driver_assignments', ['driver_id'])
    
    # Layer C: Active Tables
    
    # Create current_vehicle_assignments table
    op.create_table(
        'current_vehicle_assignments',
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('depot_id', sa.String(50), nullable=False),
        sa.Column('vehicle_id', sa.String(50), nullable=False),
        sa.Column('trip_id', sa.String(50), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('deadhead_km', sa.Numeric(10, 2), server_default='0'),
        sa.Column('deployed_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['depot_id'], ['depots.depot_id']),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.vehicle_id']),
        sa.ForeignKeyConstraint(['trip_id'], ['timetable.trip_id'])
    )
    op.create_index('idx_cva_depot', 'current_vehicle_assignments', ['depot_id'])
    op.create_index('idx_cva_vehicle', 'current_vehicle_assignments', ['vehicle_id'])
    
    # Create current_driver_assignments table
    op.create_table(
        'current_driver_assignments',
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('depot_id', sa.String(50), nullable=False),
        sa.Column('driver_id', sa.String(50), nullable=False),
        sa.Column('trip_id', sa.String(50), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('duty_hours', sa.Numeric(4, 2), nullable=False),
        sa.Column('break_minutes', sa.Integer(), server_default='0'),
        sa.Column('deployed_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['depot_id'], ['depots.depot_id']),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.driver_id']),
        sa.ForeignKeyConstraint(['trip_id'], ['timetable.trip_id'])
    )
    op.create_index('idx_cda_depot', 'current_driver_assignments', ['depot_id'])
    op.create_index('idx_cda_driver', 'current_driver_assignments', ['driver_id'])


def downgrade() -> None:
    """Drop all tables"""
    
    # Drop Layer C tables
    op.drop_table('current_driver_assignments')
    op.drop_table('current_vehicle_assignments')
    
    # Drop Layer B tables
    op.drop_table('plan_driver_assignments')
    op.drop_table('plan_vehicle_assignments')
    op.drop_table('plans')
    
    # Drop Layer A tables
    op.drop_table('timetable')
    op.drop_table('drivers')
    op.drop_table('vehicles')
    op.drop_table('routes')
    op.drop_table('stops')
    op.drop_table('depots')
