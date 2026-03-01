# PMPML Bus Optimization Backend

FastAPI-based backend system for optimizing bus fleet operations for Pune Mahanagar Parivahan Mahamandalimited (PMPML).

## Features

- **CSV Data Upload**: Upload and validate base transit data (routes, stops, vehicles, drivers, depots, timetable)
- **Time-Space Network (TSN) Building**: Construct in-memory graph representation of transit operations
- **Optimization Engine**: Google OR-Tools CP-SAT solver for optimal vehicle and driver assignments
- **Plan Management**: Create, version, and compare optimization plans per depot
- **Atomic Deployment**: Safe, transactional plan activation with depot-scoped operations
- **Driver App API**: Authentication and duty management for driver mobile applications

## Architecture

### Three-Layer Database Design

1. **Layer A - Base Data**: Immutable uploaded CSV data (routes, stops, vehicles, drivers, depots, timetable)
2. **Layer B - Plan Tables**: Optimization output with versioning (plans, assignments)
3. **Layer C - Active Tables**: Current operational data for driver apps

### Key Principles

- **Depot-Scoped Operations**: All optimization and deployment scoped to individual depots
- **Transient TSN**: Time-Space Networks built in-memory, never persisted
- **Atomic Deployment**: Single database transaction for plan activation
- **Multi-Depot Independence**: Concurrent operations on different depots without conflicts

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Optimization**: Google OR-Tools CP-SAT solver
- **Task Queue**: Celery + Redis (optional, for long-running optimizations)

## Setup

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 14 or higher
- Redis (optional, for Celery)

### Installation

1. **Clone the repository**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Create database**
   ```bash
   createdb pmpml_optimization
   ```

6. **Run migrations**
   ```bash
   alembic upgrade head
   ```

7. **Seed demo data (optional)**
   ```python
   python -c "from app.database.init_db import create_tables, seed_demo_data; from app.database.db import SessionLocal; create_tables(); db = SessionLocal(); seed_demo_data(db); db.close()"
   ```

## Running the Application

### Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Driver App Setup (Phase 1)

For driver mobile app integration:

```bash
# 1. Run database migration for driver auth
alembic upgrade head

# 2. Setup test driver credentials
python setup_driver_test_data.py

# 3. Test driver app APIs
python test_driver_app_api.py
```

**Test Credentials**: `PMPML-4521` / `test123`

See `DRIVER_APP_README.md` for complete driver app documentation.

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Data Upload
- `POST /api/data/upload/{type}` - Upload CSV for routes, stops, vehicles, drivers, depots, or timetable

### Optimization
- `POST /api/optimization/run` - Run optimization for a depot

### Plan Management
- `GET /api/plans` - List all plans (filter by depot_id)
- `GET /api/plans/active` - Get all active plans (city-wide view)
- `GET /api/plans/{id}` - Get plan details with assignments
- `POST /api/plans/{id}/deploy` - Deploy a PENDING plan
- `GET /api/plans/{id}/compare` - Compare plan metrics

### Driver App
- `POST /api/auth/login` - Driver login with JWT tokens
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout
- `GET /api/driver/profile` - Get driver profile
- `GET /api/duty/today` - Get today's duty assignment
- `GET /api/driver/{driver_id}/schedule` - Get driver's current schedule (legacy)

## Database Migrations

### Create a new migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback migration

```bash
alembic downgrade -1
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_optimization.py

# Run property-based tests
pytest tests/test_properties.py
```

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app initialization
│   ├── config.py                  # Configuration management
│   ├── api/                       # API route handlers
│   │   ├── data_routes.py
│   │   ├── optimization_routes.py
│   │   ├── plan_routes.py
│   │   └── driver_routes.py
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── base_models.py         # Layer A: Base data
│   │   └── plan_models.py         # Layer B & C: Plans and active tables
│   ├── services/                  # Business logic
│   │   ├── tsn_builder.py         # Time-Space Network construction
│   │   ├── optimizer.py           # OR-Tools solver
│   │   ├── plan_service.py        # Plan CRUD operations
│   │   └── deployment_service.py  # Atomic plan deployment
│   ├── database/                  # Database utilities
│   │   ├── db.py                  # Connection and session management
│   │   └── init_db.py             # Table creation and seeding
│   └── schemas/                   # Pydantic models
│       ├── request_schemas.py
│       └── response_schemas.py
├── alembic/                       # Database migrations
├── tests/                         # Test suite
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
└── README.md                      # This file
```

## Development Workflow

1. **Upload CSV Data**: Use POST /api/data/upload/{type} to populate base data
2. **Run Optimization**: POST /api/optimization/run with depot_id and parameters
3. **Review Plan**: GET /api/plans/{id} to see assignments and metrics
4. **Compare Plans**: GET /api/plans/{id}/compare to evaluate alternatives
5. **Deploy Plan**: POST /api/plans/{id}/deploy to activate (atomic operation)
6. **Driver App**: GET /api/driver/{driver_id}/schedule to serve schedules

## Critical Rules

- Never modify base data during optimization
- TSN is never stored in database (transient computation)
- Never auto-deploy plans (human review required)
- Deployment must be single DB transaction
- Deployment deletes/writes only by depot_id
- One ACTIVE plan per depot (not globally)
- Driver app reads only current_* tables
- Plan history never deleted
- Optimize per depot, not city-wide

## Scaling Considerations

- **Demo Scale**: 4 trips, 3 vehicles, 3 drivers, 1 depot
- **Production Scale**: 800+ trips, 120+ vehicles, 150+ drivers, 15+ depots
- **Strategy**: Always optimize per depot (never city-wide)
- **Solver Time Limit**: 120 seconds (configurable)
- **Async Execution**: Use Celery for long-running optimizations

## License

Proprietary - PMPML Bus Optimization System

## Support

For issues and questions, contact the development team.
