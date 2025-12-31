"""
API v1 router - aggregates all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import datasets, anonymization

api_router = APIRouter()

# Include dataset endpoints
api_router.include_router(
    datasets.router,
    prefix="/datasets",
    tags=["datasets"]
)

# Include anonymization endpoints
api_router.include_router(
    anonymization.router,
    prefix="/datasets",
    tags=["anonymization"]
)

# Future routers will be added here:
# api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
