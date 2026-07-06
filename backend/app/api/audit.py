from fastapi import APIRouter

from app.models.audit import AuditRequest
from app.services.audit_service import review_audit_subject


router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.post("/review")
def review_audit(request: AuditRequest):
    return review_audit_subject(request)
