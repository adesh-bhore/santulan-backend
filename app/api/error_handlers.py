"""Global Error Handlers

Centralized error handling for consistent API responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime
import traceback
import uuid

from app.schemas.error_schemas import ErrorResponse, ErrorDetail, ValidationError, ErrorCode


def create_error_response(
    message: str,
    code: str,
    status_code: int,
    details: dict = None,
    validation_errors: list = None,
    request_id: str = None
) -> JSONResponse:
    """Create standardized error response"""
    
    error_response = ErrorResponse(
        success=False,
        error=ErrorDetail(
            message=message,
            code=code,
            details=details,
            validation_errors=validation_errors
        ),
        request_id=request_id or str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors (422)"""
    
    validation_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        validation_errors.append(
            ValidationError(
                field=field or "unknown",
                message=error["msg"],
                code="VALIDATION_ERROR"
            ).model_dump()
        )
    
    return create_error_response(
        message="Validation error",
        code=ErrorCode.VALIDATION_ERROR,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        validation_errors=validation_errors,
        request_id=str(uuid.uuid4())
    )


async def http_exception_handler(request: Request, exc: Exception):
    """Handle HTTPException (400, 404, 409, etc.)"""
    
    # Extract status code and detail from HTTPException
    status_code = getattr(exc, "status_code", 500)
    detail = getattr(exc, "detail", str(exc))
    
    # Map status codes to error codes
    code_map = {
        400: ErrorCode.INVALID_INPUT,
        404: ErrorCode.DEPOT_NOT_FOUND,  # Default, can be overridden
        409: ErrorCode.DUPLICATE_ENTRY,
        422: ErrorCode.VALIDATION_ERROR,
        500: ErrorCode.INTERNAL_SERVER_ERROR
    }
    
    # Try to extract error code from detail if it's a dict
    if isinstance(detail, dict):
        code = detail.get("code", code_map.get(status_code, ErrorCode.UNEXPECTED_ERROR))
        message = detail.get("message", str(detail))
        details = detail.get("details")
    else:
        code = code_map.get(status_code, ErrorCode.UNEXPECTED_ERROR)
        message = detail
        details = None
    
    return create_error_response(
        message=message,
        code=code,
        status_code=status_code,
        details=details,
        request_id=str(uuid.uuid4())
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors (500)"""
    
    # Log the full error for debugging
    print(f"Database error: {exc}")
    traceback.print_exc()
    
    # Check for specific database errors
    if isinstance(exc, IntegrityError):
        # Foreign key or unique constraint violation
        return create_error_response(
            message="Database integrity error. The operation violates data constraints.",
            code=ErrorCode.DUPLICATE_ENTRY,
            status_code=status.HTTP_409_CONFLICT,
            details={"error": str(exc.orig) if hasattr(exc, 'orig') else str(exc)},
            request_id=str(uuid.uuid4())
        )
    
    # Generic database error
    return create_error_response(
        message="Database error occurred. Please try again later.",
        code=ErrorCode.DATABASE_ERROR,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={"error": str(exc)} if hasattr(exc, '__str__') else None,
        request_id=str(uuid.uuid4())
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all other unexpected errors (500)"""
    
    # Log the full error for debugging
    print(f"Unexpected error: {exc}")
    traceback.print_exc()
    
    return create_error_response(
        message="An unexpected error occurred. Please try again later.",
        code=ErrorCode.UNEXPECTED_ERROR,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={"error": str(exc), "type": type(exc).__name__},
        request_id=str(uuid.uuid4())
    )


def register_error_handlers(app):
    """Register all error handlers with FastAPI app"""
    
    from fastapi import HTTPException
    
    # Validation errors (422)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # HTTP exceptions (400, 404, 409, etc.)
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # Database errors (500)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    
    # Generic errors (500)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    print("✓ Error handlers registered")
