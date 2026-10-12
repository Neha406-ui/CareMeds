from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.residents import router as residents_router
from app.api.v1.prescriptions import router as prescriptions_router
from fastapi import APIRouter

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(residents_router, tags=["residents"])
router.include_router(prescriptions_router, tags=["prescriptions"])
