"""FastAPI Application Entry Point

Main application setup with routes, middleware, and startup events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.database.init_db import create_tables
from app.api.error_handlers import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting PMPML Bus Optimization Backend...")
    if settings.debug:
        print("⚠️  Debug mode enabled - creating tables if they don't exist")
        create_tables()
    print("✓ Application started successfully")
    
    yield
    
    # Shutdown
    print("👋 Shutting down application...")


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
