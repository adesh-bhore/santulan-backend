"""Authentication Service for Driver App"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.base_models import Driver, Depot
from app.config import settings

# Security configuration from settings
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_HOURS = settings.jwt_access_token_expire_hours
REFRESH_TOKEN_EXPIRE_DAYS = settings.jwt_refresh_token_expire_days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service for driver login and token management"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def authenticate_driver(db: Session, driver_id: str, password: str) -> Optional[Driver]:
        """Authenticate driver with driver_id and password"""
        driver = db.query(Driver).filter(
            Driver.driver_id == driver_id,
            Driver.is_active == True
        ).first()
        
        if not driver:
            return None
        
        # If no password hash set, allow test password for development
        if not driver.password_hash:
            # For development: accept "test123" for any driver without password
            if password == "test123":
                return driver
            return None
        
        if not AuthService.verify_password(password, driver.password_hash):
            return None
        
        return driver
    
    @staticmethod
    def get_driver_profile(db: Session, driver_id: str) -> Optional[dict]:
        """Get driver profile with depot information"""
        driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if not driver:
            return None
        
        depot = db.query(Depot).filter(Depot.depot_id == driver.depot_id).first()
        
        # Calculate duty hours this month (placeholder - would need actual tracking)
        duty_hours_this_month = 156.0  # Mock value
        duty_hours_target = float(driver.max_duty_hours) * 26  # Assuming 26 working days
        
        return {
            "id": driver.driver_id,
            "name": driver.driver_name,
            "nameMarathi": driver.name_marathi or driver.driver_name,
            "phone": driver.phone or "+91 00000 00000",
            "email": driver.email or f"{driver.driver_id}@pmpml.org",
            "depot": depot.depot_name if depot else driver.depot_id,
            "depotMarathi": depot.depot_name if depot else driver.depot_id,  # TODO: Add Marathi depot names
            "licenseNumber": driver.license_number or "MH-12-XXXX-XXXXXX",
            "rating": float(driver.rating) if driver.rating else 0.0,
            "totalTrips": driver.total_trips or 0,
            "onTimePercent": float(driver.on_time_percent) if driver.on_time_percent else 0.0,
            "safetyScore": driver.safety_score or 0,
            "dutyHoursThisMonth": duty_hours_this_month,
            "dutyHoursTarget": duty_hours_target
        }
