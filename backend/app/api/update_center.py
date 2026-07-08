from fastapi import APIRouter

from app.models.update_center import ApplicationUpdateCheckResult, UpdateCenterStatus, UpdateCheckResult
from app.services.update_center_service import check_for_application_update, check_for_updates, get_update_status


router = APIRouter(prefix="/api/v1/update-center", tags=["update-center"])


@router.get("/status")
def read_update_center_status() -> UpdateCenterStatus:
    return get_update_status()


@router.post("/check")
def check_update_center_now() -> UpdateCheckResult:
    return check_for_updates()


@router.post("/application/check")
def check_application_update_now() -> ApplicationUpdateCheckResult:
    return check_for_application_update()
