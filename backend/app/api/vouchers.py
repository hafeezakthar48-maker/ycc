from fastapi import APIRouter, File, Header, HTTPException, Query, Response, UploadFile

from app.api.upload_security import read_attachment_upload
from app.models.system_admin import AuditLogCreateRequest
from app.models.voucher import VoucherDraftRequest
from app.models.voucher_center import (
    VoucherCenterCreateRequest,
    VoucherCenterImportRequest,
    VoucherPostingRequest,
    VoucherReviewRequest,
)
from app.services.voucher_center_service import (
    attach_voucher_file,
    create_voucher,
    export_vouchers_csv,
    import_vouchers,
    list_vouchers,
    post_voucher,
    review_voucher,
    unpost_voucher,
    unreview_voucher,
    update_voucher,
)
from app.services.system_admin_service import authorize, record_audit_log
from app.services.voucher_service import generate_voucher_draft


router = APIRouter(prefix="/api/v1/vouchers", tags=["vouchers"])


@router.post("/draft")
def create_voucher_draft(request: VoucherDraftRequest):
    return generate_voucher_draft(request)


@router.get("/center")
def get_voucher_center(account_set_id: str | None = Query(default=None, min_length=1, max_length=64)):
    return list_vouchers(account_set_id)


@router.post("/center")
def create_center_voucher(
    request: VoucherCenterCreateRequest,
    x_actor_id: str = Header(default="system"),
):
    _require_voucher_permission(
        actor_id=x_actor_id,
        permission_code="voucher.create",
        event="voucher.create",
        target_id="new-voucher",
        metadata={"summary": request.summary},
    )
    voucher = create_voucher(request)
    _record_voucher_audit(
        actor_id=x_actor_id,
        event="voucher.create",
        target_id=voucher.id,
        metadata={
            "voucher_number": voucher.voucher_number,
            "account_set_id": voucher.account_set_id,
            "summary": voucher.summary,
            "total_amount_with_tax": str(voucher.total_amount_with_tax),
        },
    )
    return voucher


@router.post("/center/import")
def import_center_vouchers(
    request: VoucherCenterImportRequest,
    x_actor_id: str = Header(default="system"),
):
    _require_voucher_permission(
        actor_id=x_actor_id,
        permission_code="voucher.import",
        event="voucher.import",
        target_id="voucher-import-batch",
        metadata={"requested_count": len(request.vouchers)},
    )
    result = import_vouchers(request)
    _record_voucher_audit(
        actor_id=x_actor_id,
        event="voucher.import",
        target_id="voucher-import-batch",
        metadata={"imported_count": result.imported_count},
    )
    return result


@router.get("/center/export/csv")
def export_center_vouchers_csv(x_actor_id: str = Header(default="system")):
    _require_voucher_permission(
        actor_id=x_actor_id,
        permission_code="voucher.export",
        event="voucher.export",
        target_id="voucher-center",
        metadata={"format": "csv"},
    )
    content = export_vouchers_csv()
    _record_voucher_audit(
        actor_id=x_actor_id,
        event="voucher.export",
        target_id="voucher-center",
        metadata={"format": "csv"},
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="voucher-center.csv"'},
    )


@router.put("/center/{voucher_id}")
def update_center_voucher(
    voucher_id: str,
    request: VoucherCenterCreateRequest,
    x_actor_id: str = Header(default="system"),
):
    _require_voucher_permission(
        actor_id=x_actor_id,
        permission_code="voucher.update",
        event="voucher.update",
        target_id=voucher_id,
        metadata={"summary": request.summary},
    )
    voucher = update_voucher(voucher_id, request)
    _record_voucher_audit(
        actor_id=x_actor_id,
        event="voucher.update",
        target_id=voucher.id,
        metadata={
            "voucher_number": voucher.voucher_number,
            "account_set_id": voucher.account_set_id,
            "summary": voucher.summary,
        },
    )
    return voucher


@router.post("/center/{voucher_id}/review")
def review_center_voucher(
    voucher_id: str,
    request: VoucherReviewRequest,
    x_actor_id: str = Header(default="system"),
):
    _require_voucher_permission(
        actor_id=x_actor_id,
        permission_code="voucher.review",
        event="voucher.review",
        target_id=voucher_id,
        metadata={"reviewer": request.reviewer},
    )
    voucher = review_voucher(voucher_id, request.reviewer)
    _record_voucher_audit(
        actor_id=x_actor_id,
        event="voucher.review",
        target_id=voucher.id,
        metadata={
            "voucher_number": voucher.voucher_number,
            "account_set_id": voucher.account_set_id,
            "reviewer": request.reviewer,
        },
    )
    return voucher


@router.post("/center/{voucher_id}/unreview")
def unreview_center_voucher(
    voucher_id: str,
    x_actor_id: str = Header(default="system"),
):
    _require_voucher_permission(
        actor_id=x_actor_id,
        permission_code="voucher.unreview",
        event="voucher.unreview",
        target_id=voucher_id,
        metadata={},
    )
    voucher = unreview_voucher(voucher_id)
    _record_voucher_audit(
        actor_id=x_actor_id,
        event="voucher.unreview",
        target_id=voucher.id,
        metadata={"voucher_number": voucher.voucher_number, "account_set_id": voucher.account_set_id},
    )
    return voucher


@router.post("/center/{voucher_id}/post")
def post_center_voucher(
    voucher_id: str,
    request: VoucherPostingRequest,
    x_actor_id: str = Header(default="system"),
):
    _require_voucher_permission(
        actor_id=x_actor_id,
        permission_code="voucher.post",
        event="voucher.post",
        target_id=voucher_id,
        metadata={"operator": request.operator},
    )
    voucher = post_voucher(voucher_id, request.operator)
    _record_voucher_audit(
        actor_id=x_actor_id,
        event="voucher.post",
        target_id=voucher.id,
        metadata={
            "voucher_number": voucher.voucher_number,
            "account_set_id": voucher.account_set_id,
            "posted_by": voucher.posted_by,
            "posted_at": voucher.posted_at,
        },
    )
    return voucher


@router.post("/center/{voucher_id}/unpost")
def unpost_center_voucher(
    voucher_id: str,
    request: VoucherPostingRequest,
    x_actor_id: str = Header(default="system"),
):
    _require_voucher_permission(
        actor_id=x_actor_id,
        permission_code="voucher.unpost",
        event="voucher.unpost",
        target_id=voucher_id,
        metadata={"operator": request.operator},
    )
    voucher = unpost_voucher(voucher_id)
    _record_voucher_audit(
        actor_id=x_actor_id,
        event="voucher.unpost",
        target_id=voucher.id,
        metadata={
            "voucher_number": voucher.voucher_number,
            "account_set_id": voucher.account_set_id,
            "operator": request.operator,
        },
    )
    return voucher


@router.post("/center/{voucher_id}/attachments")
async def upload_center_voucher_attachment(
    voucher_id: str,
    file: UploadFile = File(...),
    x_actor_id: str = Header(default="system"),
):
    filename = file.filename or "attachment"
    content_type = file.content_type or "application/octet-stream"
    _require_voucher_permission(
        actor_id=x_actor_id,
        permission_code="voucher.attachment.upload",
        event="voucher.attachment.upload",
        target_id=voucher_id,
        metadata={"filename": filename, "content_type": content_type},
    )
    content = await read_attachment_upload(file)
    voucher = attach_voucher_file(
        voucher_id=voucher_id,
        filename=filename,
        content_type=content_type,
        size=len(content),
    )
    _record_voucher_audit(
        actor_id=x_actor_id,
        event="voucher.attachment.upload",
        target_id=voucher.id,
        metadata={
            "voucher_number": voucher.voucher_number,
            "account_set_id": voucher.account_set_id,
            "filename": filename,
            "content_type": content_type,
            "size": len(content),
        },
    )
    return voucher


def _record_voucher_audit(
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


def _require_voucher_permission(
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

    _record_voucher_audit(
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
