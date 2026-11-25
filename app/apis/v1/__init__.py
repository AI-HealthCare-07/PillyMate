from fastapi import APIRouter

from app.apis.v1.auth_routers import auth_router
from app.apis.v1.child_routers import child_router
from app.apis.v1.me_routers import me_router
from app.apis.v1.prescription_registration_routers import prescription_registration_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(me_router)
v1_routers.include_router(child_router)
v1_routers.include_router(prescription_registration_router)
