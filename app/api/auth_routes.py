"""Authentication API Routes for Driver App"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database.db import get_db
from app.services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_HOURS
from app.schemas.auth_schemas import (
    LoginRequest, LoginResponse, RefreshTokenRequest, RefreshTokenResponse,
    LogoutResponse, DriverProfile, ErrorResponse
)

router = APIRouter()
security = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate driver with driver_id and password, return JWT tokens.
    
    Request body must be:
    {
        "driverId": "DRV_BHSR_001",
        "password": "test123"
    }
    
    For development/testing, use:
    - Driver ID: Any valid driver_id from database (e.g., DRV_BHSR_001)
    - Password: test123 (works for drivers without password_hash set)
    """
    try:
        print(f"✅ Login attempt - driverId: {request.driverId}")
        
        # Authenticate driver using driver_id
        driver = AuthService.authenticate_driver(db, request.driverId, request.password)
        
        if not driver:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_CREDENTIALS",
                    "message": "Invalid driver ID or password",
                    "messageMarathi": "अवैध ड्रायव्हर आयडी किंवा पासवर्ड"
                }
            )
        
        # Create tokens
        token_data = {"sub": driver.driver_id}
        access_token = AuthService.create_access_token(token_data)
        refresh_token = AuthService.create_refresh_token(token_data)
        
        # Get driver profile
        profile = AuthService.get_driver_profile(db, driver.driver_id)
        
        return {
            "token": access_token,
            "refreshToken": refresh_token,
            "expiresIn": ACCESS_TOKEN_EXPIRE_HOURS * 3600,
            "driver": profile
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "messageMarathi": "एक अनपेक्षित त्रुटी आली. कृपया पुन्हा प्रयत्न करा."
            }
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh JWT access token using refresh token.
    """
    try:
        # Decode refresh token
        payload = AuthService.decode_token(request.refreshToken)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_TOKEN",
                    "message": "Invalid or expired refresh token",
                    "messageMarathi": "अवैध किंवा कालबाह्य रिफ्रेश टोकन"
                }
            )
        
        driver_id = payload.get("sub")
        
        # Create new access token
        token_data = {"sub": driver_id}
        access_token = AuthService.create_access_token(token_data)
        
        return {
            "token": access_token,
            "expiresIn": ACCESS_TOKEN_EXPIRE_HOURS * 3600
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "messageMarathi": "एक अनपेक्षित त्रुटी आली. कृपया पुन्हा प्रयत्न करा."
            }
        )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Invalidate current session and tokens.
    
    Note: With JWT, we can't truly invalidate tokens server-side without a blacklist.
    This endpoint is provided for client-side cleanup and future blacklist implementation.
    """
    try:
        # Verify token is valid
        token = credentials.credentials
        payload = AuthService.decode_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "UNAUTHORIZED",
                    "message": "Invalid or expired token",
                    "messageMarathi": "अवैध किंवा कालबाह्य टोकन"
                }
            )
        
        # TODO: Add token to blacklist in production
        
        return {
            "success": True,
            "message": "Logged out successfully",
            "messageMarathi": "यशस्वीरित्या लॉग आउट झाले"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "messageMarathi": "एक अनपेक्षित त्रुटी आली. कृपया पुन्हा प्रयत्न करा."
            }
        )


def get_current_driver(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    Dependency to get current authenticated driver from token.
    Use this in protected endpoints.
    """
    token = credentials.credentials
    payload = AuthService.decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Invalid or expired token",
                "messageMarathi": "अवैध किंवा कालबाह्य टोकन"
            }
        )
    
    driver_id = payload.get("sub")
    profile = AuthService.get_driver_profile(db, driver_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNAUTHORIZED",
                "message": "Driver not found",
                "messageMarathi": "ड्रायव्हर सापडला नाही"
            }
        )
    
    return profile
