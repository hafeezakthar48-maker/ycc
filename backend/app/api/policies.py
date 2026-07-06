from fastapi import APIRouter

from app.models.policy import PolicySearchRequest
from app.services.policy_library_service import search_policy_documents


router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


@router.post("/search")
def search_policies(request: PolicySearchRequest):
    return search_policy_documents(request)
