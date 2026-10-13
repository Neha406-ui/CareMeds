from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.residents import router as residents_router
from app.api.v1.prescriptions import router as prescriptions_router
from app.api.v1.doses import router as doses_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.operations import router as operations_router
from app.api.v1.analytics import router as analytics_router
from fastapi import APIRouter

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(residents_router, tags=["residents"])
router.include_router(prescriptions_router, tags=["prescriptions"])
router.include_router(doses_router, tags=["doses"])
router.include_router(notifications_router, tags=["notifications"])
router.include_router(inventory_router, tags=["inventory"])
router.include_router(operations_router, tags=["operations"])
router.include_router(analytics_router, tags=["analytics"])
