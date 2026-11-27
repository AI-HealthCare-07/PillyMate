from fastapi import APIRouter

from app.apis.v1.auth_routers import auth_router
from app.apis.v1.chat_routers import chat_router
from app.apis.v1.child_routers import child_router
from app.apis.v1.me_routers import me_router
from app.apis.v1.medication_alarm_routers import medication_alarm_router
from app.apis.v1.medication_dose_routers import medication_dose_router
from app.apis.v1.prescription_deletion_routers import prescription_deletion_router
from app.apis.v1.prescription_query_routers import prescription_query_router
from app.apis.v1.prescription_registration_routers import prescription_registration_router
from app.apis.v1.prescription_routers import prescription_router
from app.apis.v1.push_routers import push_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(me_router)
v1_routers.include_router(child_router)
v1_routers.include_router(prescription_registration_router)
v1_routers.include_router(prescription_query_router)
v1_routers.include_router(prescription_deletion_router)
v1_routers.include_router(prescription_router)
v1_routers.include_router(chat_router)
v1_routers.include_router(medication_alarm_router)
v1_routers.include_router(medication_dose_router)
v1_routers.include_router(push_router)
