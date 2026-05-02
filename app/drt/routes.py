"""API Routes for Commuter DRT Ping System"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database.db import get_db
from app.drt.schemas import (
    CommuterRegisterRequest,
    CommuterLoginRequest,
    CommuterResponse,
    CommuterAuthResponse,
    PingRequest,
    PingResponse,
    PingHistoryResponse,
    PingStatsResponse,
    SurgeEventResponse,
    SurgeDetailResponse,
    SurgeApprovalRequest,
    SurgeRejectionRequest,
    UnscheduledTripResponse,
    # Phase 3 schemas
    PassengerCountRequest,
    PassengerCountResponse,
    TripSuppressionResponse,
    SuppressionDetailResponse,
    SuppressionApprovalRequest,
    SuppressionRejectionRequest,
    SuppressionAnalyticsResponse,
    DemandTrendResponse
)
from app.drt.services import CommuterService
from app.drt.surge import SurgeService
from app.services.auth_service import AuthService
from app.models.base_models import Stop, Route
from app.drt import models


router = APIRouter()


@router.post("/register", response_model=CommuterResponse, status_code=status.HTTP_201_CREATED)
async def register_commuter(
    request: CommuterRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new commuter for DRT ping system.
    
    - **phone**: Phone number (required, unique)
    - **name**: Commuter name (optional)
    - **email**: Email address (optional)
    - **password**: Password (optional, defaults to test123 for development)
    """
    try:
        commuter = CommuterService.register_commuter(
            db=db,
            phone=request.phone,
            name=request.name,
            email=request.email,
            password=request.password
        )
        
        return commuter
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=CommuterAuthResponse)
async def login_commuter(
    request: CommuterLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login commuter and get JWT token.
    
    - **phone**: Phone number
    - **password**: Password (use 'test123' for development if no password set)
    """
    try:
        # Authenticate commuter
        commuter = CommuterService.authenticate_commuter(
            db=db,
            phone=request.phone,
            password=request.password
        )
        
        if not commuter:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid phone number or password"
            )
        
        # Create JWT token
        token_data = {
            "sub": commuter.commuter_id,
            "phone": commuter.phone,
            "role": "commuter"
        }
        access_token = AuthService.create_access_token(token_data)
        
        return CommuterAuthResponse(
            token=access_token,
            commuter=CommuterResponse.from_orm(commuter),
            expiresIn=86400
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/ping", response_model=PingResponse, status_code=status.HTTP_201_CREATED)
async def create_ping(
    request: PingRequest,
    commuter_id: str,
    db: Session = Depends(get_db)
):
    """
    Create a new ping from commuter location.
    
    - **latitude**: GPS latitude
    - **longitude**: GPS longitude
    - **ping_metadata**: Additional metadata (optional)
    
    The system will automatically detect the nearest bus stop within 500m radius.
    """
    try:
        # Create ping and detect stop
        ping, detected_stop = CommuterService.create_ping(
            db=db,
            commuter_id=commuter_id,
            latitude=request.latitude,
            longitude=request.longitude,
            ping_metadata=request.ping_metadata
        )
        
        # Build response message
        if detected_stop:
            message = f"Ping recorded at {detected_stop.stop_name} ({ping.distance_to_stop_m:.0f}m away)"
        else:
            message = "Ping recorded. No bus stop detected within 500m radius."
        
        return PingResponse(
            ping_id=ping.ping_id,
            commuter_id=ping.commuter_id,
            latitude=float(ping.latitude),
            longitude=float(ping.longitude),
            detected_stop_id=ping.detected_stop_id,
            detected_stop_name=detected_stop.stop_name if detected_stop else None,
            distance_to_stop_m=float(ping.distance_to_stop_m) if ping.distance_to_stop_m else None,
            ping_time=ping.ping_time,
            status=ping.status,
            message=message
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ping creation failed: {str(e)}"
        )


@router.get("/ping/history", response_model=List[PingHistoryResponse])
async def get_ping_history(
    commuter_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get ping history for commuter.
    
    - **commuter_id**: Commuter ID (from JWT token)
    - **limit**: Maximum number of pings to return (default: 50)
    """
    try:
        pings = CommuterService.get_ping_history(
            db=db,
            commuter_id=commuter_id,
            limit=limit
        )
        
        # Get stop names
        stop_ids = [p.detected_stop_id for p in pings if p.detected_stop_id]
        stops_dict = {}
        if stop_ids:
            stops = db.query(Stop).filter(Stop.stop_id.in_(stop_ids)).all()
            stops_dict = {s.stop_id: s.stop_name for s in stops}
        
        # Build response
        result = []
        for ping in pings:
            result.append(PingHistoryResponse(
                ping_id=ping.ping_id,
                latitude=float(ping.latitude),
                longitude=float(ping.longitude),
                detected_stop_id=ping.detected_stop_id,
                detected_stop_name=stops_dict.get(ping.detected_stop_id) if ping.detected_stop_id else None,
                distance_to_stop_m=float(ping.distance_to_stop_m) if ping.distance_to_stop_m else None,
                ping_time=ping.ping_time,
                status=ping.status
            ))
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ping history: {str(e)}"
        )


@router.get("/ping/stats", response_model=PingStatsResponse)
async def get_ping_stats(
    commuter_id: str,
    db: Session = Depends(get_db)
):
    """
    Get ping statistics for commuter.
    
    - **commuter_id**: Commuter ID (from JWT token)
    """
    try:
        stats = CommuterService.get_ping_stats(db=db, commuter_id=commuter_id)
        return PingStatsResponse(**stats)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ping stats: {str(e)}"
        )


@router.get("/profile", response_model=CommuterResponse)
async def get_commuter_profile(
    commuter_id: str,
    db: Session = Depends(get_db)
):
    """
    Get commuter profile.
    
    - **commuter_id**: Commuter ID (from JWT token)
    """
    try:
        commuter = CommuterService.get_commuter(db=db, commuter_id=commuter_id)
        
        if not commuter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commuter not found"
            )
        
        return commuter
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch profile: {str(e)}"
        )



# Phase 2: Surge Management Endpoints

@router.get("/surge/active", response_model=List[SurgeEventResponse])
async def get_active_surges(
    depot_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all active (pending) surge events.
    
    - **depot_id**: Optional depot filter
    
    Requires supervisor role.
    """
    try:
        service = SurgeService(db)
        surges = service.get_active_surges(depot_id=depot_id)
        
        # Get stop names
        stop_ids = [s.stop_id for s in surges]
        stops_dict = {}
        if stop_ids:
            stops = db.query(Stop).filter(Stop.stop_id.in_(stop_ids)).all()
            stops_dict = {s.stop_id: s.stop_name for s in stops}
        
        # Build response
        result = []
        for surge in surges:
            result.append(SurgeEventResponse(
                surge_id=surge.surge_id,
                stop_id=surge.stop_id,
                stop_name=stops_dict.get(surge.stop_id),
                route_ids=surge.route_ids if isinstance(surge.route_ids, list) else [],
                ping_count=surge.ping_count,
                detected_at=surge.detected_at,
                status=surge.status,
                approved_by=surge.approved_by,
                approved_at=surge.approved_at,
                rejected_by=surge.rejected_by,
                rejected_at=surge.rejected_at,
                rejection_reason=surge.rejection_reason
            ))
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch active surges: {str(e)}"
        )


@router.get("/surge/history", response_model=List[SurgeEventResponse])
async def get_surge_history(
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get surge event history.
    
    - **limit**: Maximum number of records (default: 50)
    - **status_filter**: Optional status filter (pending/approved/rejected)
    
    Requires supervisor role.
    """
    try:
        service = SurgeService(db)
        surges = service.get_surge_history(limit=limit, status=status_filter)
        
        # Get stop names
        stop_ids = [s.stop_id for s in surges]
        stops_dict = {}
        if stop_ids:
            stops = db.query(Stop).filter(Stop.stop_id.in_(stop_ids)).all()
            stops_dict = {s.stop_id: s.stop_name for s in stops}
        
        # Build response
        result = []
        for surge in surges:
            result.append(SurgeEventResponse(
                surge_id=surge.surge_id,
                stop_id=surge.stop_id,
                stop_name=stops_dict.get(surge.stop_id),
                route_ids=surge.route_ids if isinstance(surge.route_ids, list) else [],
                ping_count=surge.ping_count,
                detected_at=surge.detected_at,
                status=surge.status,
                approved_by=surge.approved_by,
                approved_at=surge.approved_at,
                rejected_by=surge.rejected_by,
                rejected_at=surge.rejected_at,
                rejection_reason=surge.rejection_reason
            ))
        
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch surge history: {str(e)}"
        )


@router.get("/surge/{surge_id}", response_model=SurgeDetailResponse)
async def get_surge_detail(
    surge_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed surge information including ping details.
    
    - **surge_id**: Surge event ID
    
    Requires supervisor role.
    """
    try:
        service = SurgeService(db)
        detail = service.get_surge_detail(surge_id)
        
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Surge {surge_id} not found"
            )
        
        surge = detail['surge']
        stop = detail['stop']
        pings = detail['pings']
        
        return SurgeDetailResponse(
            surge_id=surge.surge_id,
            stop_id=surge.stop_id,
            stop_name=stop.stop_name if stop else None,
            route_ids=surge.route_ids if isinstance(surge.route_ids, list) else [],
            ping_count=surge.ping_count,
            detected_at=surge.detected_at,
            status=surge.status,
            pings=pings
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch surge detail: {str(e)}"
        )


@router.post("/surge/{surge_id}/approve", response_model=UnscheduledTripResponse, status_code=status.HTTP_201_CREATED)
async def approve_surge(
    surge_id: int,
    request: SurgeApprovalRequest,
    supervisor_id: str,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """
    Approve a surge event and create an unscheduled trip.
    
    - **surge_id**: Surge event ID
    - **route_id**: Route to dispatch
    - **vehicle_id**: Vehicle to assign
    - **driver_id**: Driver to assign
    - **start_stop_id**: Start stop
    - **end_stop_id**: End stop
    - **scheduled_start_time**: When trip should start
    - **notes**: Optional notes
    
    Requires supervisor role.
    """
    try:
        service = SurgeService(db)
        unscheduled_trip = service.approve_surge(
            surge_id=surge_id,
            route_id=request.route_id,
            vehicle_id=request.vehicle_id,
            driver_id=request.driver_id,
            start_stop_id=request.start_stop_id,
            end_stop_id=request.end_stop_id,
            scheduled_start_time=request.scheduled_start_time,
            approved_by=supervisor_id,
            notes=request.notes
        )
        
        return unscheduled_trip
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve surge: {str(e)}"
        )


@router.post("/surge/{surge_id}/reject", response_model=SurgeEventResponse)
async def reject_surge(
    surge_id: int,
    request: SurgeRejectionRequest,
    supervisor_id: str,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """
    Reject a surge event.
    
    - **surge_id**: Surge event ID
    - **reason**: Reason for rejection (minimum 10 characters)
    
    Requires supervisor role.
    """
    try:
        service = SurgeService(db)
        surge = service.reject_surge(
            surge_id=surge_id,
            rejected_by=supervisor_id,
            reason=request.reason
        )
        
        # Get stop name
        stop = db.query(Stop).filter(Stop.stop_id == surge.stop_id).first()
        
        return SurgeEventResponse(
            surge_id=surge.surge_id,
            stop_id=surge.stop_id,
            stop_name=stop.stop_name if stop else None,
            route_ids=surge.route_ids if isinstance(surge.route_ids, list) else [],
            ping_count=surge.ping_count,
            detected_at=surge.detected_at,
            status=surge.status,
            approved_by=surge.approved_by,
            approved_at=surge.approved_at,
            rejected_by=surge.rejected_by,
            rejected_at=surge.rejected_at,
            rejection_reason=surge.rejection_reason
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject surge: {str(e)}"
        )




# ========================================
# Phase 3: Ghost Bus Suppression Endpoints
# ========================================

@router.post("/passenger-count", response_model=PassengerCountResponse, status_code=status.HTTP_201_CREATED)
async def record_passenger_count(
    request: PassengerCountRequest,
    db: Session = Depends(get_db)
):
    """
    Record passenger count for a trip.
    
    - **trip_id**: Trip ID
    - **route_id**: Route ID
    - **passenger_count**: Total passenger count
    - **trip_date**: Trip date
    - **trip_time**: Trip time
    - **source**: Source of count (manual, automatic, estimated)
    
    Requires supervisor or driver role.
    """
    try:
        from app.drt.passenger_count import PassengerCountService
        
        service = PassengerCountService(db)
        count = service.record_count(
            trip_id=request.trip_id,
            route_id=request.route_id,
            passenger_count=request.passenger_count,
            trip_date=request.trip_date,
            trip_time=request.trip_time,
            source=request.source,
            vehicle_id=request.vehicle_id,
            driver_id=request.driver_id,
            boarding_count=request.boarding_count,
            alighting_count=request.alighting_count,
            recorded_by=request.recorded_by
        )
        
        return count
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record passenger count: {str(e)}"
        )


@router.get("/passenger-count/route/{route_id}", response_model=List[PassengerCountResponse])
async def get_route_passenger_counts(
    route_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get historical passenger counts for a route.
    
    - **route_id**: Route ID
    - **days**: Number of days to retrieve (default: 30)
    
    Requires supervisor role.
    """
    try:
        from app.drt.passenger_count import PassengerCountService
        
        service = PassengerCountService(db)
        counts = service.get_historical_counts(route_id=route_id, days=days)
        
        return counts
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch passenger counts: {str(e)}"
        )


@router.get("/suppression/pending", response_model=List[TripSuppressionResponse])
async def get_pending_suppressions(
    route_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all pending suppression recommendations.
    
    - **route_id**: Optional route filter
    
    Requires supervisor role.
    """
    try:
        from app.drt.ghost_bus import GhostBusService
        
        service = GhostBusService(db)
        suppressions = service.get_pending_suppressions(route_id=route_id)
        
        return suppressions
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending suppressions: {str(e)}"
        )


@router.get("/suppression/{suppression_id}", response_model=SuppressionDetailResponse)
async def get_suppression_detail(
    suppression_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed suppression information.
    
    - **suppression_id**: Suppression ID
    
    Requires supervisor role.
    """
    try:
        from app.drt.ghost_bus import GhostBusService
        from app.drt.passenger_count import PassengerCountService
        
        # Get suppression
        suppression = db.query(models.TripSuppression).filter(
            models.TripSuppression.suppression_id == suppression_id
        ).first()
        
        if not suppression:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Suppression {suppression_id} not found"
            )
        
        # Get historical counts
        count_service = PassengerCountService(db)
        historical_counts = count_service.get_historical_counts(
            route_id=suppression.route_id,
            days=30
        )
        
        # Calculate average
        avg_count = count_service.calculate_average(
            route_id=suppression.route_id,
            days=30
        )
        
        # Get route name
        route = db.query(Route).filter(Route.route_id == suppression.route_id).first()
        route_name = route.route_name if route else None
        
        return SuppressionDetailResponse(
            suppression=suppression,
            historical_counts=historical_counts,
            route_name=route_name,
            avg_count_last_30_days=avg_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch suppression detail: {str(e)}"
        )


@router.post("/suppression/{suppression_id}/approve", response_model=TripSuppressionResponse)
async def approve_suppression(
    suppression_id: int,
    request: SuppressionApprovalRequest,
    supervisor_id: str,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """
    Approve a suppression recommendation.
    
    - **suppression_id**: Suppression ID
    - **notes**: Optional notes
    
    Requires supervisor role.
    """
    try:
        from app.drt.ghost_bus import GhostBusService
        
        service = GhostBusService(db)
        suppression = service.approve_suppression(
            suppression_id=suppression_id,
            supervisor_id=supervisor_id,
            notes=request.notes
        )
        
        return suppression
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve suppression: {str(e)}"
        )


@router.post("/suppression/{suppression_id}/reject", response_model=TripSuppressionResponse)
async def reject_suppression(
    suppression_id: int,
    request: SuppressionRejectionRequest,
    supervisor_id: str,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """
    Reject a suppression recommendation.
    
    - **suppression_id**: Suppression ID
    - **reason**: Rejection reason (minimum 10 characters)
    
    Requires supervisor role.
    """
    try:
        from app.drt.ghost_bus import GhostBusService
        
        # Validate reason
        if len(request.reason) < 10:
            raise ValueError("Rejection reason must be at least 10 characters")
        
        service = GhostBusService(db)
        suppression = service.reject_suppression(
            suppression_id=suppression_id,
            supervisor_id=supervisor_id,
            reason=request.reason
        )
        
        return suppression
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject suppression: {str(e)}"
        )


@router.get("/suppression/history", response_model=List[TripSuppressionResponse])
async def get_suppression_history(
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get suppression history.
    
    - **limit**: Maximum number of records (default: 50)
    - **status_filter**: Optional status filter (pending/approved/rejected/executed)
    
    Requires supervisor role.
    """
    try:
        from app.drt.ghost_bus import GhostBusService
        
        service = GhostBusService(db)
        suppressions = service.get_suppression_history(
            limit=limit,
            status=status_filter
        )
        
        return suppressions
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch suppression history: {str(e)}"
        )


@router.get("/analytics/suppression", response_model=SuppressionAnalyticsResponse)
async def get_suppression_analytics(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Get suppression analytics for date range.
    
    - **start_date**: Start date (YYYY-MM-DD)
    - **end_date**: End date (YYYY-MM-DD)
    
    Requires supervisor role.
    """
    try:
        from app.drt.ghost_bus import GhostBusService
        
        service = GhostBusService(db)
        analytics = service.get_suppression_analytics(
            start_date=start_date,
            end_date=end_date
        )
        
        return analytics
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch suppression analytics: {str(e)}"
        )


@router.get("/analytics/demand-trends", response_model=List[DemandTrendResponse])
async def get_demand_trends(
    route_id: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get demand trends over time.
    
    - **route_id**: Optional route filter
    - **days**: Number of days to analyze (default: 30)
    
    Requires supervisor role.
    """
    try:
        from app.drt.passenger_count import PassengerCountService
        
        service = PassengerCountService(db)
        trends = service.get_demand_trends(route_id=route_id, days=days)
        
        # Get route names
        route_ids = list(set([t['route_id'] for t in trends]))
        routes = db.query(Route).filter(Route.route_id.in_(route_ids)).all()
        route_names = {r.route_id: r.route_name for r in routes}
        
        # Add route names to trends
        for trend in trends:
            trend['route_name'] = route_names.get(trend['route_id'])
        
        return trends
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch demand trends: {str(e)}"
        )
