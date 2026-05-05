"""FastAPI Application Entry Point

Main application setup with routes, middleware, and startup events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os

from app.config import settings
from app.database.init_db import create_tables
from app.api.error_handlers import register_error_handlers

# DRT Phase 2: APScheduler for background jobs
from apscheduler.schedulers.background import BackgroundScheduler
from app.database.db import SessionLocal

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def run_clustering_job_with_db():
    """Wrapper to run clustering job with database session"""
    from app.drt.clustering import ClusteringService
    
    db = SessionLocal()
    try:
        service = ClusteringService(db)
        result = service.run_clustering_job()
        logger.info(f"Clustering job completed: {result}")
    except Exception as e:
        logger.error(f"Clustering job failed: {str(e)}", exc_info=True)
    finally:
        db.close()


def run_daily_analysis_with_db():
    """Wrapper to run daily analysis job with database session"""
    from app.drt.analysis_job import run_daily_analysis
    
    db = SessionLocal()
    try:
        result = run_daily_analysis(db)
        logger.info(f"Daily analysis job completed: {result}")
    except Exception as e:
        logger.error(f"Daily analysis job failed: {str(e)}", exc_info=True)
    finally:
        db.close()


def run_daily_ping_cleanup():
    """Wrapper to run daily ping cleanup at midnight"""
    from app.drt.models import CommuterPing, SurgeEvent
    
    db = SessionLocal()
    try:
        # Delete ALL pings (fresh start each day)
        ping_count = db.query(CommuterPing).count()
        logger.info(f"Daily cleanup: Found {ping_count} pings to delete")
        
        db.query(CommuterPing).delete()
        
        # Also clean up old surge events (keep only today's)
        from datetime import datetime
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        old_surges = db.query(SurgeEvent).filter(
            SurgeEvent.detected_at < today_start
        ).delete()
        
        db.commit()
        logger.info(f"Daily cleanup completed: Deleted {ping_count} pings and {old_surges} old surge events")
        
        return {
            'status': 'success',
            'pings_deleted': ping_count,
            'surges_deleted': old_surges
        }
    
    except Exception as e:
        logger.error(f"Daily ping cleanup failed: {str(e)}", exc_info=True)
        db.rollback()
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting PMPML Bus Optimization Backend...")
    if settings.debug:
        print("⚠️  Debug mode enabled - creating tables if they don't exist")
        create_tables()
    
    # Start DRT clustering job if enabled
    if settings.drt_clustering_enabled:
        print(f"✓ Starting DRT clustering job (every {settings.drt_clustering_interval_minutes} minutes)")
        scheduler.add_job(
            run_clustering_job_with_db,
            'interval',
            minutes=settings.drt_clustering_interval_minutes,
            id='drt_clustering',
            replace_existing=True
        )
        scheduler.start()
    else:
        print("⚠️  DRT clustering disabled via config")
    
    # Start DRT daily analysis job if enabled (Phase 3)
    analysis_enabled = os.getenv('DRT_ANALYSIS_JOB_ENABLED', 'True').lower() == 'true'
    if analysis_enabled:
        analysis_time = os.getenv('DRT_ANALYSIS_JOB_TIME', '02:00')
        hour, minute = map(int, analysis_time.split(':'))
        print(f"✓ Starting DRT daily analysis job (daily at {analysis_time})")
        scheduler.add_job(
            run_daily_analysis_with_db,
            'cron',
            hour=hour,
            minute=minute,
            id='drt_daily_analysis',
            replace_existing=True
        )
        if not scheduler.running:
            scheduler.start()
    else:
        print("⚠️  DRT daily analysis disabled via config")
    
    # Start daily ping cleanup job (runs at midnight)
    print("✓ Starting daily ping cleanup job (daily at 00:00)")
    scheduler.add_job(
        run_daily_ping_cleanup,
        'cron',
        hour=0,
        minute=0,
        id='drt_daily_ping_cleanup',
        replace_existing=True
    )
    if not scheduler.running:
        scheduler.start()
    
    print("✓ Application started successfully")
    
    yield
    
    # Shutdown
    print("👋 Shutting down application...")
    if scheduler.running:
        scheduler.shutdown()
        print("✓ Scheduler shut down")


# Create FastAPI application
app = FastAPI(
    title="PMPML Bus Optimization API",
    description="""
    Backend API for PMPML bus fleet optimization and scheduling.
    
    ## Features
    
    * **Data Upload**: Upload CSV files for routes, stops, vehicles, drivers, depots, and timetables
    * **Optimization**: Run optimization engine to generate optimal vehicle and driver schedules
    * **Plan Management**: Create, view, compare, and deploy optimization plans
    * **Driver App**: Retrieve driver schedules and assignments
    
    ## Authentication
    
    Currently no authentication required (development mode).
    
    ## Error Handling
    
    All errors return a standardized JSON format:
    ```json
    {
        "success": false,
        "error": {
            "message": "Human-readable error message",
            "code": "MACHINE_READABLE_CODE",
            "details": {},
            "validation_errors": []
        },
        "request_id": "req_abc123",
        "timestamp": "2024-02-25T10:30:00Z"
    }
    ```
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware - MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for mobile app
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to client
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Register error handlers
register_error_handlers(app)

# Add custom validation error handler for debugging
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"❌ Validation Error on {request.url}")
    print(f"   Body: {await request.body()}")
    print(f"   Errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request data",
            "messageMarathi": "अवैध विनंती डेटा",
            "details": exc.errors()
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "pmpml-backend",
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "PMPML Bus Optimization API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Register API routes
from app.api import (
    data_routes, optimization_routes, plan_routes, driver_routes, 
    report_routes, dashboard_routes, auth_routes, duty_routes, driver_profile_routes, trip_routes
)
from app.drt import routes as drt_routes

app.include_router(dashboard_routes.router, prefix="/api", tags=["Dashboard"])
app.include_router(data_routes.router, prefix="/api/data", tags=["Data Upload"])
app.include_router(optimization_routes.router, prefix="/api/optimization", tags=["Optimization"])
app.include_router(plan_routes.router, prefix="/api", tags=["Plan Management"])
app.include_router(driver_routes.router, prefix="/api", tags=["Driver App - Legacy"])
app.include_router(report_routes.router, prefix="/api", tags=["Reports"])

# Driver App Phase 1 APIs
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Driver App - Authentication"])
app.include_router(duty_routes.router, prefix="/api/duty", tags=["Driver App - Duty Management"])
app.include_router(driver_profile_routes.router, prefix="/api/driver", tags=["Driver App - Profile"])
app.include_router(trip_routes.router, prefix="/api", tags=["Driver App - Trip Management"])

# DRT Ping Schedule APIs (Isolated Module)
app.include_router(drt_routes.router, prefix="/api/drt", tags=["DRT - Ping Schedule"])


# DRT WebSocket endpoint for real-time surge notifications
from fastapi import WebSocket, WebSocketDisconnect, Query
from app.drt.websocket import surge_ws_manager
from app.services.auth_service import AuthService

@app.websocket("/ws/drt/surge")
async def websocket_surge_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    depot_id: str = Query("ALL", description="Depot ID to monitor (default: ALL)")
):
    """
    WebSocket endpoint for real-time surge notifications.
    
    **Authentication**: Requires valid JWT token with supervisor role.
    
    **Parameters**:
    - `token`: JWT access token (query parameter)
    - `depot_id`: Depot ID to monitor (default: "ALL" for all depots)
    
    **Message Format**:
    ```json
    {
        "type": "surge_detected",
        "data": {
            "surge_id": 123,
            "stop_id": "STOP_SWGT",
            "stop_name": "Swargate Bus Stand",
            "route_ids": ["ROUTE_101", "ROUTE_102"],
            "ping_count": 52,
            "detected_at": "2024-02-25T10:30:00Z"
        },
        "timestamp": "2024-02-25T10:30:00Z"
    }
    ```
    
    **Keep-alive**: Server sends ping every 30 seconds. Client should respond with pong.
    """
    try:
        # Validate JWT token
        try:
            payload = AuthService.decode_access_token(token)
            role = payload.get("role")
            
            # Only supervisors can connect
            if role != "supervisor":
                await websocket.close(code=1008, reason="Unauthorized: supervisor role required")
                return
        
        except Exception as e:
            await websocket.close(code=1008, reason=f"Invalid token: {str(e)}")
            return
        
        # Accept connection
        connected = await surge_ws_manager.connect(websocket, depot_id)
        
        if not connected:
            return  # Connection limit reached
        
        try:
            # Keep connection alive and handle messages
            while True:
                # Wait for messages from client (e.g., pong responses)
                data = await websocket.receive_text()
                
                # Echo back for debugging (optional)
                if data == "ping":
                    await websocket.send_text("pong")
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for depot {depot_id}")
        
        finally:
            surge_ws_manager.disconnect(websocket, depot_id)
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
