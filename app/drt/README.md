# DRT (Demand-Responsive Transit) Module

## Overview

This module implements the "Ping Schedule" feature for PMPML - a demand-responsive transit system that allows commuters to request bus service based on real-time demand.

**Current Phase**: Phase 1 - Commuter Ping System  
**Status**: ✅ Complete  
**Version**: 1.0.0

---

## Module Structure

```
backend/app/drt/
├── __init__.py          # Module initialization
├── README.md            # This file
├── models.py            # SQLAlchemy models (Commuter, CommuterPing)
├── schemas.py           # Pydantic request/response schemas
├── services.py          # Business logic (CommuterService)
└── routes.py            # FastAPI endpoints
```

---

## Why Isolated?

The DRT module is kept separate from the core optimization system for several reasons:

1. **Maintainability**: Easy to locate and modify DRT-specific code
2. **Scalability**: Can be extracted as a microservice if needed
3. **Clarity**: Clear separation between optimization and DRT features
4. **Testing**: Isolated testing without affecting core system
5. **Team Collaboration**: Different teams can work on DRT vs optimization

---

## API Endpoints

All DRT endpoints are under `/api/drt`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/drt/register` | Register new commuter |
| POST | `/api/drt/login` | Login and get JWT token |
| POST | `/api/drt/ping` | Create GPS ping |
| GET | `/api/drt/ping/history` | Get ping history |
| GET | `/api/drt/ping/stats` | Get ping statistics |
| GET | `/api/drt/profile` | Get commuter profile |

---

## Database Tables

### `commuters`
Stores commuter registration and profile data.

**Columns**:
- `commuter_id` (PK) - Unique identifier (COM_XXXXXXXX)
- `phone` (UNIQUE) - Phone number (10+ digits)
- `name` - Commuter name (optional)
- `email` - Email address (optional)
- `password_hash` - Hashed password
- `is_active` - Account status
- `total_pings` - Total pings count
- `created_at`, `updated_at` - Timestamps

**Indexes**:
- `ix_commuters_phone` (unique)
- `ix_commuters_is_active`

### `commuter_pings`
Stores GPS ping data with stop detection.

**Columns**:
- `ping_id` (PK) - Auto-increment ID
- `commuter_id` (FK) - Reference to commuter
- `latitude`, `longitude` - GPS coordinates
- `detected_stop_id` (FK) - Nearest stop (if within 500m)
- `distance_to_stop_m` - Distance to detected stop
- `ping_time` - When ping was created
- `status` - Ping status (pending/processed/surge_triggered)
- `surge_event_id` - Reference to surge event (Phase 2)
- `metadata` - JSON field for additional data
- `created_at` - Timestamp

**Indexes**:
- `ix_commuter_pings_commuter_id`
- `ix_commuter_pings_detected_stop_id`
- `ix_commuter_pings_ping_time`
- `ix_commuter_pings_status`
- `ix_commuter_pings_surge_event_id`

---

## Key Features

### 1. Commuter Registration & Authentication
- Phone-based registration
- JWT authentication with role: "commuter"
- Password hashing with bcrypt
- Development mode: accepts "test123" as default password

### 2. GPS Ping System
- Accepts latitude/longitude coordinates
- Automatic stop detection within 500m radius
- Haversine distance calculation
- Returns stop name and distance

### 3. Stop Detection Algorithm
```python
def _detect_nearest_stop(latitude, longitude):
    1. Get all stops from database
    2. Calculate Haversine distance to each stop
    3. Find minimum distance
    4. If distance <= 500m, return stop
    5. Otherwise, return None
```

### 4. Ping History & Statistics
- View last 50 pings
- Statistics: total, pending, processed, surge-triggered
- Includes stop names and distances

---

## Usage Examples

### Register Commuter
```python
from app.drt.services import CommuterService
from app.database.db import get_db

db = next(get_db())
commuter = CommuterService.register_commuter(
    db=db,
    phone="9876543210",
    name="John Doe",
    password="securepass123"
)
```

### Create Ping
```python
ping, detected_stop = CommuterService.create_ping(
    db=db,
    commuter_id="COM_A1B2C3D4",
    latitude=18.5018,
    longitude=73.8636
)

if detected_stop:
    print(f"Detected stop: {detected_stop.stop_name}")
    print(f"Distance: {ping.distance_to_stop_m}m")
```

### Get Ping History
```python
pings = CommuterService.get_ping_history(
    db=db,
    commuter_id="COM_A1B2C3D4",
    limit=10
)
```

---

## Configuration

DRT settings in `app/config.py`:

```python
# DRT Ping Schedule Configuration
drt_stop_detection_radius_m: int = 500
drt_surge_ping_threshold: int = 50
drt_clustering_interval_minutes: int = 5
drt_ping_expiry_minutes: int = 30
```

Environment variables (`.env`):
```env
DRT_STOP_DETECTION_RADIUS_M=500
DRT_SURGE_PING_THRESHOLD=50
DRT_CLUSTERING_INTERVAL_MINUTES=5
DRT_PING_EXPIRY_MINUTES=30
```

---

## Dependencies

### Internal Dependencies
- `app.models.base_models.Base` - SQLAlchemy base class
- `app.models.base_models.Stop` - Stop model for detection
- `app.services.auth_service.AuthService` - JWT and password hashing
- `app.database.db.get_db` - Database session

### External Dependencies
- `fastapi` - API framework
- `sqlalchemy` - ORM
- `pydantic` - Schema validation
- `passlib` - Password hashing
- `python-jose` - JWT tokens

---

## Testing

### Run Test Script
```bash
cd backend
python test_phase1_commuter_ping.py
```

### Manual Testing
```bash
# Register
curl -X POST http://localhost:8000/api/drt/register \
  -H "Content-Type: application/json" \
  -d '{"phone":"9876543210","name":"Test","password":"test123"}'

# Login
curl -X POST http://localhost:8000/api/drt/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"9876543210","password":"test123"}'

# Create Ping
curl -X POST "http://localhost:8000/api/drt/ping?commuter_id=COM_XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{"latitude":18.5018,"longitude":73.8636}'
```

---

## Future Phases

### Phase 2: Surge Detection & Dispatch (Weeks 3-4)
- Clustering service (group pings by route corridor)
- Surge detection (50+ pings threshold)
- Supervisor approval workflow
- Unscheduled trip creation
- WebSocket notifications

**New Files**:
- `app/drt/clustering.py` - Clustering algorithm
- `app/drt/surge.py` - Surge detection logic
- `app/drt/websocket.py` - Real-time notifications

### Phase 3: Ghost Bus Suppression (Weeks 5-6)
- Ghost bus detection
- Integration with optimization engine
- Passenger count tracking
- Suppression logic

**New Files**:
- `app/drt/ghost_bus.py` - Ghost bus detection
- `app/drt/optimization_integration.py` - Optimizer integration

---

## Migration

Database migration: `backend/alembic/versions/004_add_commuter_and_pings.py`

```bash
# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## Documentation

- **Feature Docs**: `backend/DRT_PHASE1_README.md`
- **Deployment**: `backend/DRT_PHASE1_DEPLOYMENT.md`
- **Testing**: `backend/PHASE1_TESTING_CHECKLIST.md`
- **Requirements**: `.kiro/specs/drt-ping-schedule/requirements.md`
- **Design**: `.kiro/specs/drt-ping-schedule/design.md`
- **Tasks**: `.kiro/specs/drt-ping-schedule/tasks.md`

---

## Support

For issues or questions:
1. Check module README (this file)
2. Review API documentation: `http://localhost:8000/docs`
3. Check backend logs: `sudo journalctl -u pmpml-backend -f`
4. Refer to spec documents in `.kiro/specs/drt-ping-schedule/`

---

## Module Maintainers

- **Phase 1**: Commuter Ping System - Complete
- **Phase 2**: Surge Detection - Upcoming
- **Phase 3**: Ghost Bus Suppression - Upcoming

**Last Updated**: April 4, 2026  
**Version**: 1.0.0
