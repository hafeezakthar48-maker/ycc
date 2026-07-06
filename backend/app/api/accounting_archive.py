from fastapi import APIRouter, Header, HTTPException, Query, Response

from app.models.accounting_archive import ArchiveCase, ArchiveCaseCreate, ArchiveDocument, ArchiveDocumentListResponse
from app.models.system_admin import AuditLogCreateRequest
from app.services.accounting_archive_service import (
    build_archive_package,
    create_archive_case,
    get_archive_case,
    get_archive_document,
    list_archive_documents,
)
from app.services.system_admin_service import authorize, record_audit_log


router = APIRouter(prefix="/api/v1/accounting-archive", tags=["accounting-archive"])


@router.get("/documents", response_model=ArchiveDocumentListResponse)
def list_documents(
    account_set_id: str = Query(default="default", min_length=1, max_length=64),
    period: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    x_actor_id: str = Header(default="system"),
):
    event = "archive.document.list"
    target_id = f"archive-documents:{account_set_id}:{period or 'all'}"
    metadata = {"account_set_id": account_set_id, "period": period or ""}
    _require_archive_permission(
        actor_id=x_actor_id,
        permission_code="archive.read",
        event=event,
        target_id=target_id,
        metadata=metadata,
    )
    response = list_archive_documents(account_set_id=account_set_id, period=period)
    _record_archive_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=target_id,
        metadata={**metadata, "document_count": response.total},
    )
    return response


@router.get("/documents/{archive_document_id}", response_model=ArchiveDocument)
def get_document(archive_document_id: str, x_actor_id: str = Header(default="system")):
    event = "archive.document.get"
    _require_archive_permission(
        actor_id=x_actor_id,
        permission_code="archive.read",
        event=event,
        target_id=archive_document_id,
        metadata={"archive_document_id": archive_document_id},
    )
    try:
        document = get_archive_document(archive_document_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    _record_archive_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=document.archive_document_id,
        metadata={
            "account_set_id": document.account_set_id,
            "period": document.period,
            "filename": document.filename,
            "sha256_hash": document.sha256_hash,
        },
    )
    return document


@router.post("/cases", response_model=ArchiveCase)
def create_case(request: ArchiveCaseCreate, x_actor_id: str = Header(default="system")):
    event = "archive.case.create"
    target_id = f"archive-case:{request.account_set_id}:{request.period}:{request.case_type}"
    metadata = {
        "account_set_id": request.account_set_id,
        "period": request.period,
        "case_type": request.case_type,
        "document_count": len(request.document_ids),
    }
    _require_archive_permission(
        actor_id=x_actor_id,
        permission_code="archive.case.create",
        event=event,
        target_id=target_id,
        metadata=metadata,
    )
    try:
        archive_case = create_archive_case(request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    _record_archive_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=archive_case.archive_case_id,
        metadata={
            **metadata,
            "archive_case_id": archive_case.archive_case_id,
            "archive_status": archive_case.archive_status,
        },
    )
    return archive_case


@router.get("/cases/{archive_case_id}/download")
def download_case_package(archive_case_id: str, x_actor_id: str = Header(default="system")):
    event = "archive.package.download"
    _require_archive_permission(
        actor_id=x_actor_id,
        permission_code="archive.package.download",
        event=event,
        target_id=archive_case_id,
        metadata={"archive_case_id": archive_case_id},
    )
    try:
        archive_case = get_archive_case(archive_case_id)
        payload = build_archive_package(archive_case_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    _record_archive_audit(
        actor_id=x_actor_id,
        event=event,
        target_id=archive_case.archive_case_id,
        metadata={
            "account_set_id": archive_case.account_set_id,
            "period": archive_case.period,
            "case_type": archive_case.case_type,
            "document_count": archive_case.document_count,
            "filename": payload.filename,
        },
    )
    return Response(
        content=payload.content,
        media_type=payload.content_type,
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )


def _record_archive_audit(
    actor_id: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
    result: str = "success",
) -> None:
    record_audit_log(
        AuditLogCreateRequest(
            actor_id=actor_id,
            module_id="finance-center",
            event=event,
            target_id=target_id,
            result=result,
            metadata=metadata,
        )
    )


def _require_archive_permission(
    actor_id: str,
    permission_code: str,
    event: str,
    target_id: str,
    metadata: dict[str, str | int | float | bool | None],
) -> None:
    if actor_id == "system":
        return

    decision = authorize(actor_id, permission_code)
    if decision.allowed:
        return

    _record_archive_audit(
        actor_id=actor_id,
        event=event,
        target_id=target_id,
        result="denied",
        metadata={
            **metadata,
            "permission_code": permission_code,
            "reason": decision.reason,
        },
    )
    raise HTTPException(status_code=403, detail=decision.reason)
