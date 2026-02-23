"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log any unhandled exception."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # Special handling for Pydantic serialization errors
    # These often happen in the response layer
    if "PydanticSerializationError" in str(type(exc)):
        logger.error("DETECTION: PydanticSerializationError detected in response layer!")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Erreur de sérialisation des données (NumPy int64/float64).",
                "error_type": "PydanticSerializationError",
                "message": str(exc)
            }
        )
        
    return JSONResponse(
        status_code=500,
        content={"detail": "Une erreur interne est survenue.", "message": str(exc)}
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status indicating the service is healthy
    """
    return {"status": "healthy", "service": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/")
async def root():
    """
    Root endpoint with API information.

    Returns:
        dict: Welcome message and API details
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# Include API routers
from app.api.v1.router import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)
