# Formal Accounting Engine Phase 7 Electronic Voucher Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在正式核算与报表归档基础上，建立电子凭证和会计档案底座，支持来源文件留存、文件哈希、OCR/验真状态、凭证附件归档、保管期限、档案目录和归档审计。
**Architecture:** 新增 `accounting_archive` 领域模型与服务，凭证中心附件上传后生成可归档的电子凭证文档，文档通过 `source_type/source_id` 关联凭证、正式分录、固定资产、工资批次或报表快照。归档服务只保存文件元数据、内容哈希、可选文本内容和档案状态，不伪造 OCR 或验真结论；真实 OCR/发票验真引擎缺失时记录 `verification_status="pending_external"`。
**Tech Stack:** FastAPI、Pydantic、SQLite、hashlib、zipfile、pytest、React、TypeScript、Vite、Node test runner。
---

## Prerequisite

必须先完成并验证：
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-1.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-4-period-close.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-6-statement-export-archive.md`
- 后端已有凭证中心附件上传入口 `POST /api/v1/vouchers/center/{voucher_id}/attachments`
- 后端已有 OCR 文本解析和图片/PDF 缺失引擎提示，不伪造 OCR 结果
- 后端已有权限与审计日志服务
- 前端已有凭证中心附件上传区和 OCR 发票识别区

本期不做 CA 签章、电子发票服务平台实时验真、对象存储、WORM 存储、长期冷备、电子会计档案国标全量字段、跨系统档案移交和档案销毁审批。本期先把凭证证据链、档案目录、哈希校验、保管期限和归档包下载做成可验证的最小闭环。

## Accounting Decisions

- 档案文档以 `archive_document_id` 为唯一标识，不复用凭证附件 ID。
- 每个文档必须保存 `sha256_hash`、`filename`、`content_type`、`size`、`source_type`、`source_id`、`account_set_id` 和 `period`。
- 本地 MVP 不永久保存二进制原文到数据库；默认保存元数据和可选文本摘录。归档包下载时只包含元数据 JSON、文本摘录和校验清单。
- 已接入真实文件存储后，`storage_uri` 指向受控文件位置；没有真实存储时 `storage_uri` 为空并明确标记 `storage_status="metadata_only"`。
- OCR 状态和验真状态分开：`ocr_status` 表示识别处理状态，`verification_status` 表示发票/回单/合同真实性复核状态。
- 图片/PDF 没有 OCR 引擎时，`ocr_status="engine_required"`，不能填充识别字段。
- 发票外部验真未接入时，`verification_status="pending_external"`，不能标记为 `verified`。
- 会计档案保管期限按档案类型默认配置：凭证、账簿、报表和其他会计资料默认 30 年；系统配置允许后续扩展。
- 已关闭期间可以新增归档文档，但新增行为必须记录审计日志；不能修改已锁定凭证、分录或报表快照。
- 归档包必须包含目录清单、文件哈希、关联对象和校验结果，便于后续迁移到正式档案系统。

## File Structure

- Create: `backend/app/models/accounting_archive.py`
  - 定义档案文档、档案案卷、保管期限、OCR/验真状态、归档包和下载响应模型。
- Create: `backend/app/services/accounting_archive_service.py`
  - 创建档案文档、计算哈希、关联凭证附件、维护案卷、生成归档包清单。
- Create: `backend/app/api/accounting_archive.py`
  - 提供档案文档列表、详情、凭证附件归档、案卷创建、案卷下载 API。
- Modify: `backend/app/api/router_registry.py`
  - 注册会计档案 API。
- Modify: `backend/app/models/voucher_center.py`
  - 凭证附件增加 `archive_document_id`、`sha256_hash`、`storage_status`。
- Modify: `backend/app/services/voucher_center_service.py`
  - 上传附件时计算哈希并调用归档服务创建档案文档。
- Modify: `backend/app/api/vouchers.py`
  - 附件上传审计记录增加档案文档 ID 和哈希。
- Modify: `backend/app/services/invoice_ocr_service.py`
  - 暴露文本 OCR 结果到档案文档摘录，不改变缺失引擎行为。
- Modify: `backend/app/services/system_admin_service.py`
  - 增加档案查看、归档、下载、验真状态维护权限。
- Modify: `backend/app/services/module_registry_service.py`
  - 注册档案 API、权限和审计事件。
- Create: `backend/tests/test_accounting_archive_service.py`
- Create: `backend/tests/test_accounting_archive_api.py`
- Modify: `backend/tests/test_voucher_center_service.py`
- Modify: `backend/tests/test_voucher_center_permission_api.py`
- Create: `frontend/src/types/accountingArchive.ts`
- Modify: `frontend/src/types/voucherCenter.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/AccountingArchivePanel.tsx`
- Modify: `frontend/src/components/VoucherCenterPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/accountingArchiveApi.test.mjs`
- Create: `frontend/tests/accountingArchivePanel.test.mjs`
- Modify: `frontend/tests/voucherCenterPanel.test.mjs`
- Modify: `frontend/package.json`
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 会计档案模型与文档哈希服务

**Files:**
- Create: `backend/app/models/accounting_archive.py`
- Create: `backend/app/services/accounting_archive_service.py`
- Create: `backend/tests/test_accounting_archive_service.py`

- [ ] **Step 1: Write failing archive document tests**

Create `backend/tests/test_accounting_archive_service.py`:

```python
from app.models.accounting_archive import ArchiveDocumentCreate
from app.services.accounting_archive_service import (
    create_archive_document,
    get_archive_document,
    list_archive_documents,
    reset_accounting_archive_store,
)


def setup_function():
    reset_accounting_archive_store()


def test_create_archive_document_calculates_hash_and_retention():
    document = create_archive_document(
        ArchiveDocumentCreate(
            account_set_id="default",
            period="2026-06",
            source_type="voucher",
            source_id="voucher-001",
            document_type="invoice",
            filename="invoice.txt",
            content_type="text/plain",
            content_bytes=b"invoice text",
            extracted_text="invoice text",
            uploaded_by="finance-user",
        )
    )

    loaded = get_archive_document(document.archive_document_id)
    listed = list_archive_documents(account_set_id="default", period="2026-06")

    assert document.sha256_hash == "9adcc70a5f32964ef54c16a3f3e2138f3bfe85e88b12402b248e8f28a1b2a884"
    assert document.retention_years == 30
    assert document.storage_status == "metadata_only"
    assert loaded.archive_document_id == document.archive_document_id
    assert listed.total == 1
```

- [ ] **Step 2: Implement archive models**

Create `backend/app/models/accounting_archive.py`:

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ArchiveSourceType = Literal["voucher", "journal_entry", "fixed_asset", "payroll", "statement_snapshot", "manual"]
ArchiveDocumentType = Literal["invoice", "bank_receipt", "contract", "delivery_note", "voucher_attachment", "statement", "other"]
ArchiveStatus = Literal["draft", "indexed", "archived", "locked"]
ArchiveStorageStatus = Literal["metadata_only", "stored"]
ArchiveOcrStatus = Literal["not_required", "text_parsed", "engine_required", "failed"]
ArchiveVerificationStatus = Literal["not_required", "pending_external", "verified", "failed"]


class ArchiveDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = "default"
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    source_type: ArchiveSourceType
    source_id: str
    document_type: ArchiveDocumentType
    filename: str
    content_type: str
    content_bytes: bytes
    extracted_text: str = ""
    uploaded_by: str
    storage_uri: str | None = None


class ArchiveDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archive_document_id: str
    account_set_id: str
    period: str
    source_type: ArchiveSourceType
    source_id: str
    document_type: ArchiveDocumentType
    filename: str
    content_type: str
    size: int
    sha256_hash: str
    storage_status: ArchiveStorageStatus
    storage_uri: str | None = None
    archive_status: ArchiveStatus = "indexed"
    ocr_status: ArchiveOcrStatus
    verification_status: ArchiveVerificationStatus
    retention_years: int
    extracted_text: str = ""
    uploaded_by: str
    created_at: str


class ArchiveDocumentListResponse(BaseModel):
    total: int
    documents: list[ArchiveDocument]
```

- [ ] **Step 3: Implement archive service**

Create `backend/app/services/accounting_archive_service.py`:

```python
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from app.models.accounting_archive import (
    ArchiveDocument,
    ArchiveDocumentCreate,
    ArchiveDocumentListResponse,
)

_ARCHIVE_DOCUMENTS: dict[str, ArchiveDocument] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_accounting_archive_store() -> None:
    _ARCHIVE_DOCUMENTS.clear()


def create_archive_document(payload: ArchiveDocumentCreate) -> ArchiveDocument:
    sha256_hash = hashlib.sha256(payload.content_bytes).hexdigest()
    document = ArchiveDocument(
        archive_document_id=f"arch_doc_{uuid4().hex}",
        account_set_id=payload.account_set_id,
        period=payload.period,
        source_type=payload.source_type,
        source_id=payload.source_id,
        document_type=payload.document_type,
        filename=payload.filename,
        content_type=payload.content_type,
        size=len(payload.content_bytes),
        sha256_hash=sha256_hash,
        storage_status="stored" if payload.storage_uri else "metadata_only",
        storage_uri=payload.storage_uri,
        ocr_status=_ocr_status(payload.filename, payload.content_type, payload.extracted_text),
        verification_status=_verification_status(payload.document_type),
        retention_years=_retention_years(payload.document_type),
        extracted_text=payload.extracted_text,
        uploaded_by=payload.uploaded_by,
        created_at=_now_iso(),
    )
    _ARCHIVE_DOCUMENTS[document.archive_document_id] = document
    return document


def get_archive_document(archive_document_id: str) -> ArchiveDocument:
    document = _ARCHIVE_DOCUMENTS.get(archive_document_id)
    if document is None:
        raise ValueError(f"未找到会计档案文档 {archive_document_id}")
    return document


def list_archive_documents(account_set_id: str, period: str | None = None) -> ArchiveDocumentListResponse:
    documents = [
        document for document in _ARCHIVE_DOCUMENTS.values()
        if document.account_set_id == account_set_id and (period is None or document.period == period)
    ]
    documents.sort(key=lambda item: item.created_at, reverse=True)
    return ArchiveDocumentListResponse(total=len(documents), documents=documents)
```

Add helpers:

```python
def _ocr_status(filename: str, content_type: str, extracted_text: str) -> str:
    if extracted_text:
        return "text_parsed"
    if filename.lower().endswith(".txt") or content_type.startswith("text/"):
        return "text_parsed"
    if content_type.startswith("image/") or content_type == "application/pdf":
        return "engine_required"
    return "not_required"


def _verification_status(document_type: str) -> str:
    if document_type in {"invoice", "bank_receipt"}:
        return "pending_external"
    return "not_required"


def _retention_years(document_type: str) -> int:
    if document_type in {"invoice", "bank_receipt", "contract", "voucher_attachment", "statement"}:
        return 30
    return 10
```

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_accounting_archive_service.py
git add backend/app/models/accounting_archive.py backend/app/services/accounting_archive_service.py backend/tests/test_accounting_archive_service.py
git commit -m "feat: add accounting archive documents"
```

## Task 2: 凭证附件归档联动

**Files:**
- Modify: `backend/app/models/voucher_center.py`
- Modify: `backend/app/services/voucher_center_service.py`
- Modify: `backend/tests/test_voucher_center_service.py`
- Modify: `backend/tests/test_accounting_archive_service.py`

- [ ] **Step 1: Write failing voucher attachment archive tests**

Append to `backend/tests/test_voucher_center_service.py`:

```python
from app.services.accounting_archive_service import get_archive_document, reset_accounting_archive_store


def test_attach_voucher_file_creates_archive_document():
    reset_accounting_archive_store()
    voucher = create_voucher(_request())

    updated = attach_voucher_file(
        voucher_id=voucher.id,
        filename="invoice.txt",
        content_type="text/plain",
        size=12,
        content_bytes=b"invoice text",
        uploaded_by="finance-user",
    )

    attachment = updated.attachments[0]
    document = get_archive_document(attachment.archive_document_id)

    assert attachment.sha256_hash == document.sha256_hash
    assert attachment.storage_status == "metadata_only"
    assert document.source_type == "voucher"
    assert document.source_id == voucher.id
```

- [ ] **Step 2: Extend voucher attachment model**

In `backend/app/models/voucher_center.py`, update `VoucherAttachment`:

```python
class VoucherAttachment(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    ocr_status: str
    archive_document_id: str | None = None
    sha256_hash: str | None = None
    storage_status: str = "metadata_only"
```

- [ ] **Step 3: Link voucher attachment upload to archive service**

In `backend/app/services/voucher_center_service.py`, change function signature:

```python
def attach_voucher_file(
    voucher_id: str,
    filename: str,
    content_type: str,
    size: int,
    content_bytes: bytes,
    uploaded_by: str,
) -> VoucherCenterRecord:
```

Implementation:

```python
from app.models.accounting_archive import ArchiveDocumentCreate
from app.services.accounting_archive_service import create_archive_document
```

```python
def attach_voucher_file(
    voucher_id: str,
    filename: str,
    content_type: str,
    size: int,
    content_bytes: bytes,
    uploaded_by: str,
) -> VoucherCenterRecord:
    voucher = _get_voucher(voucher_id)
    extracted_text = content_bytes.decode("utf-8", errors="ignore") if content_type.startswith("text/") or filename.lower().endswith(".txt") else ""
    document = create_archive_document(
        ArchiveDocumentCreate(
            account_set_id=voucher.account_set_id,
            period=voucher.voucher_date[:7],
            source_type="voucher",
            source_id=voucher.id,
            document_type=_document_type_from_file(filename, content_type),
            filename=filename,
            content_type=content_type,
            content_bytes=content_bytes,
            extracted_text=extracted_text,
            uploaded_by=uploaded_by,
        )
    )
    attachment = VoucherAttachment(
        id=f"attachment-{uuid4().hex[:12]}",
        filename=filename,
        content_type=content_type,
        size=size,
        ocr_status=document.ocr_status,
        archive_document_id=document.archive_document_id,
        sha256_hash=document.sha256_hash,
        storage_status=document.storage_status,
    )
    updated = voucher.model_copy(update={"attachments": [*voucher.attachments, attachment]})
    with _connection() as connection:
        _save_voucher(connection, updated)
    return updated
```

Add helper:

```python
def _document_type_from_file(filename: str, content_type: str) -> str:
    lower_name = filename.lower()
    if "invoice" in lower_name or "发票" in filename:
        return "invoice"
    if "receipt" in lower_name or "回单" in filename:
        return "bank_receipt"
    if "contract" in lower_name or "合同" in filename:
        return "contract"
    if content_type == "application/pdf" or content_type.startswith("image/") or content_type.startswith("text/"):
        return "voucher_attachment"
    return "other"
```

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_voucher_center_service.py backend/tests/test_accounting_archive_service.py
git add backend/app/models/voucher_center.py backend/app/services/voucher_center_service.py backend/tests/test_voucher_center_service.py backend/tests/test_accounting_archive_service.py
git commit -m "feat: archive voucher attachments"
```

## Task 3: 会计档案案卷与归档包

**Files:**
- Modify: `backend/app/models/accounting_archive.py`
- Modify: `backend/app/services/accounting_archive_service.py`
- Modify: `backend/tests/test_accounting_archive_service.py`

- [ ] **Step 1: Write failing archive case tests**

Append to `backend/tests/test_accounting_archive_service.py`:

```python
from app.models.accounting_archive import ArchiveCaseCreate
from app.services.accounting_archive_service import create_archive_case, build_archive_package


def test_create_archive_case_and_build_package_manifest():
    document = create_archive_document(
        ArchiveDocumentCreate(
            account_set_id="default",
            period="2026-06",
            source_type="voucher",
            source_id="voucher-001",
            document_type="invoice",
            filename="invoice.txt",
            content_type="text/plain",
            content_bytes=b"invoice text",
            extracted_text="invoice text",
            uploaded_by="finance-user",
        )
    )

    archive_case = create_archive_case(
        ArchiveCaseCreate(
            account_set_id="default",
            period="2026-06",
            case_type="voucher",
            title="2026-06 凭证档案",
            document_ids=[document.archive_document_id],
            created_by="finance-manager",
        )
    )
    package = build_archive_package(archive_case.archive_case_id)

    assert archive_case.document_count == 1
    assert package.filename == "accounting-archive-default-2026-06-voucher.zip"
    assert package.content.startswith(b"PK")
```

- [ ] **Step 2: Add archive case models**

In `backend/app/models/accounting_archive.py`:

```python
ArchiveCaseType = Literal["voucher", "ledger", "statement", "mixed"]


class ArchiveCaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_set_id: str = "default"
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    case_type: ArchiveCaseType
    title: str
    document_ids: list[str] = Field(min_length=1, max_length=500)
    created_by: str


class ArchiveCase(BaseModel):
    archive_case_id: str
    account_set_id: str
    period: str
    case_type: ArchiveCaseType
    title: str
    document_ids: list[str]
    document_count: int
    archive_status: ArchiveStatus = "archived"
    retention_years: int
    created_by: str
    created_at: str


class ArchivePackagePayload(BaseModel):
    archive_case_id: str
    filename: str
    content_type: str
    content: bytes
```

- [ ] **Step 3: Implement archive case and package**

In `backend/app/services/accounting_archive_service.py`:

```python
import json
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.models.accounting_archive import ArchiveCase, ArchiveCaseCreate, ArchivePackagePayload

_ARCHIVE_CASES: dict[str, ArchiveCase] = {}
```

Update reset:

```python
def reset_accounting_archive_store() -> None:
    _ARCHIVE_DOCUMENTS.clear()
    _ARCHIVE_CASES.clear()
```

Add functions:

```python
def create_archive_case(payload: ArchiveCaseCreate) -> ArchiveCase:
    for document_id in payload.document_ids:
        get_archive_document(document_id)
    archive_case = ArchiveCase(
        archive_case_id=f"arch_case_{uuid4().hex}",
        account_set_id=payload.account_set_id,
        period=payload.period,
        case_type=payload.case_type,
        title=payload.title,
        document_ids=payload.document_ids,
        document_count=len(payload.document_ids),
        retention_years=30,
        created_by=payload.created_by,
        created_at=_now_iso(),
    )
    _ARCHIVE_CASES[archive_case.archive_case_id] = archive_case
    return archive_case


def get_archive_case(archive_case_id: str) -> ArchiveCase:
    archive_case = _ARCHIVE_CASES.get(archive_case_id)
    if archive_case is None:
        raise ValueError(f"未找到会计档案案卷 {archive_case_id}")
    return archive_case


def build_archive_package(archive_case_id: str) -> ArchivePackagePayload:
    archive_case = get_archive_case(archive_case_id)
    documents = [get_archive_document(document_id) for document_id in archive_case.document_ids]
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("manifest.json", _manifest_json(archive_case, documents))
        for document in documents:
            package.writestr(
                f"documents/{document.archive_document_id}.json",
                document.model_dump_json(indent=2),
            )
            if document.extracted_text:
                package.writestr(
                    f"text/{document.archive_document_id}.txt",
                    document.extracted_text,
                )
    return ArchivePackagePayload(
        archive_case_id=archive_case.archive_case_id,
        filename=f"accounting-archive-{archive_case.account_set_id}-{archive_case.period}-{archive_case.case_type}.zip",
        content_type="application/zip",
        content=output.getvalue(),
    )
```

Add manifest helper:

```python
def _manifest_json(archive_case: ArchiveCase, documents: list[ArchiveDocument]) -> str:
    payload = {
        "archive_case_id": archive_case.archive_case_id,
        "account_set_id": archive_case.account_set_id,
        "period": archive_case.period,
        "case_type": archive_case.case_type,
        "title": archive_case.title,
        "document_count": archive_case.document_count,
        "retention_years": archive_case.retention_years,
        "documents": [
            {
                "archive_document_id": document.archive_document_id,
                "filename": document.filename,
                "sha256_hash": document.sha256_hash,
                "source_type": document.source_type,
                "source_id": document.source_id,
                "ocr_status": document.ocr_status,
                "verification_status": document.verification_status,
            }
            for document in documents
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_accounting_archive_service.py
git add backend/app/models/accounting_archive.py backend/app/services/accounting_archive_service.py backend/tests/test_accounting_archive_service.py
git commit -m "feat: build accounting archive packages"
```

## Task 4: 会计档案 API、权限与审计

**Files:**
- Create: `backend/app/api/accounting_archive.py`
- Modify: `backend/app/api/router_registry.py`
- Modify: `backend/app/api/vouchers.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Create: `backend/tests/test_accounting_archive_api.py`
- Modify: `backend/tests/test_voucher_center_permission_api.py`

- [ ] **Step 1: Write failing archive API tests**

Create `backend/tests/test_accounting_archive_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.models.accounting_archive import ArchiveDocumentCreate
from app.services.accounting_archive_service import create_archive_document, reset_accounting_archive_store
from app.services.system_admin_service import reset_system_admin_store

client = TestClient(app)


def setup_function():
    reset_accounting_archive_store()
    reset_system_admin_store()


def test_archive_documents_endpoint_lists_documents():
    create_archive_document(
        ArchiveDocumentCreate(
            account_set_id="default",
            period="2026-06",
            source_type="voucher",
            source_id="voucher-001",
            document_type="invoice",
            filename="invoice.txt",
            content_type="text/plain",
            content_bytes=b"invoice text",
            extracted_text="invoice text",
            uploaded_by="finance-user",
        )
    )

    response = client.get(
        "/api/v1/accounting-archive/documents?account_set_id=default&period=2026-06",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_archive_package_download_returns_zip():
    document = create_archive_document(
        ArchiveDocumentCreate(
            account_set_id="default",
            period="2026-06",
            source_type="voucher",
            source_id="voucher-001",
            document_type="invoice",
            filename="invoice.txt",
            content_type="text/plain",
            content_bytes=b"invoice text",
            extracted_text="invoice text",
            uploaded_by="finance-user",
        )
    )
    case_response = client.post(
        "/api/v1/accounting-archive/cases",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={
            "account_set_id": "default",
            "period": "2026-06",
            "case_type": "voucher",
            "title": "2026-06 凭证档案",
            "document_ids": [document.archive_document_id],
            "created_by": "finance-manager",
        },
    )

    archive_case_id = case_response.json()["archive_case_id"]
    download_response = client.get(
        f"/api/v1/accounting-archive/cases/{archive_case_id}/download",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/zip"
    assert download_response.content.startswith(b"PK")
```

- [ ] **Step 2: Implement archive API routes**

Create `backend/app/api/accounting_archive.py`:

```python
from fastapi import APIRouter, Header, HTTPException, Response

from app.models.accounting_archive import ArchiveCaseCreate
from app.models.system_admin import AuditLogCreateRequest
from app.services.accounting_archive_service import (
    build_archive_package,
    create_archive_case,
    get_archive_document,
    list_archive_documents,
)
from app.services.system_admin_service import authorize, record_audit_log

router = APIRouter(prefix="/api/v1/accounting-archive", tags=["accounting-archive"])
```

Add routes:

```python
@router.get("/documents")
def list_documents(account_set_id: str = "default", period: str | None = None, x_actor_id: str = Header(default="system")):
    _require_archive_permission(
        actor_id=x_actor_id,
        permission_code="archive.read",
        event="archive.document.list",
        target_id=f"archive-documents:{account_set_id}:{period or 'all'}",
        metadata={"account_set_id": account_set_id, "period": period or ""},
    )
    return list_archive_documents(account_set_id=account_set_id, period=period)


@router.get("/documents/{archive_document_id}")
def get_document(archive_document_id: str, x_actor_id: str = Header(default="system")):
    _require_archive_permission(
        actor_id=x_actor_id,
        permission_code="archive.read",
        event="archive.document.get",
        target_id=archive_document_id,
        metadata={"archive_document_id": archive_document_id},
    )
    try:
        return get_archive_document(archive_document_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
```

Add case routes:

```python
@router.post("/cases")
def create_case(request: ArchiveCaseCreate, x_actor_id: str = Header(default="system")):
    _require_archive_permission(
        actor_id=x_actor_id,
        permission_code="archive.case.create",
        event="archive.case.create",
        target_id=f"archive-case:{request.account_set_id}:{request.period}",
        metadata={"period": request.period, "document_count": len(request.document_ids)},
    )
    archive_case = create_archive_case(request)
    _record_archive_audit(
        actor_id=x_actor_id,
        event="archive.case.create",
        target_id=archive_case.archive_case_id,
        metadata={"period": archive_case.period, "document_count": archive_case.document_count},
    )
    return archive_case


@router.get("/cases/{archive_case_id}/download")
def download_case(archive_case_id: str, x_actor_id: str = Header(default="system")):
    _require_archive_permission(
        actor_id=x_actor_id,
        permission_code="archive.package.download",
        event="archive.package.download",
        target_id=archive_case_id,
        metadata={"archive_case_id": archive_case_id},
    )
    try:
        payload = build_archive_package(archive_case_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    _record_archive_audit(
        actor_id=x_actor_id,
        event="archive.package.download",
        target_id=archive_case_id,
        metadata={"filename": payload.filename},
    )
    return Response(
        content=payload.content,
        media_type=payload.content_type,
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )
```

Add permission helpers:

```python
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
        metadata={**metadata, "permission_code": permission_code, "reason": decision.reason},
    )
    raise HTTPException(status_code=403, detail=decision.reason)
```

- [ ] **Step 3: Wire router and voucher upload**

In `backend/app/api/router_registry.py`, include:

```python
from app.api import accounting_archive
```

and register:

```python
app.include_router(accounting_archive.router)
```

In `backend/app/api/vouchers.py`, update attachment call:

```python
voucher = attach_voucher_file(
    voucher_id=voucher_id,
    filename=filename,
    content_type=content_type,
    size=len(content),
    content_bytes=content,
    uploaded_by=x_actor_id,
)
```

Add audit metadata:

```python
"archive_document_id": voucher.attachments[-1].archive_document_id,
"sha256_hash": voucher.attachments[-1].sha256_hash,
```

- [ ] **Step 4: Register permissions and audit events**

In `backend/app/services/system_admin_service.py`, add permissions:
- `archive.read`
- `archive.document.create`
- `archive.case.create`
- `archive.package.download`
- `archive.verification.update`

Finance manager gets all five. Auditor gets `archive.read` and `archive.package.download`.

In `backend/app/services/module_registry_service.py`, add API prefix:
- `/api/v1/accounting-archive`

Audit events:
- `archive.document.list`
- `archive.document.get`
- `archive.document.create`
- `archive.case.create`
- `archive.package.download`
- `archive.verification.update`

- [ ] **Step 5: Verify and commit**

```powershell
python -m pytest backend/tests/test_accounting_archive_api.py backend/tests/test_accounting_archive_service.py backend/tests/test_voucher_center_permission_api.py backend/tests/test_system_admin_api.py
git add backend/app/api/accounting_archive.py backend/app/api/router_registry.py backend/app/api/vouchers.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_accounting_archive_api.py backend/tests/test_voucher_center_permission_api.py
git commit -m "feat: expose accounting archive api"
```

## Task 5: 前端会计档案面板

**Files:**
- Create: `frontend/src/types/accountingArchive.ts`
- Modify: `frontend/src/types/voucherCenter.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/AccountingArchivePanel.tsx`
- Modify: `frontend/src/components/VoucherCenterPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/accountingArchiveApi.test.mjs`
- Create: `frontend/tests/accountingArchivePanel.test.mjs`
- Modify: `frontend/tests/voucherCenterPanel.test.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: Write frontend API tests**

Create `frontend/tests/accountingArchiveApi.test.mjs`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import {
  createAccountingArchiveCase,
  downloadAccountingArchivePackage,
  fetchAccountingArchiveDocuments
} from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    const payload = payloads[url] ?? payloads.default;
    return {
      ok: true,
      status: 200,
      headers: new Map([["content-disposition", 'attachment; filename="accounting-archive-default-2026-06-voucher.zip"']]),
      json: async () => payload,
      blob: async () => new Blob(["zip"])
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("会计档案 API helper 获取文档、创建案卷并下载归档包", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/accounting-archive/documents?account_set_id=default&period=2026-06": {
      total: 1,
      documents: [{ archive_document_id: "arch_doc_1", filename: "invoice.txt" }]
    },
    "http://api.local/api/v1/accounting-archive/cases": {
      archive_case_id: "arch_case_1",
      document_count: 1
    },
    default: {}
  });

  const documents = await fetchAccountingArchiveDocuments("default", "2026-06", "http://api.local", fetcher);
  const archiveCase = await createAccountingArchiveCase(
    {
      account_set_id: "default",
      period: "2026-06",
      case_type: "voucher",
      title: "2026-06 凭证档案",
      document_ids: ["arch_doc_1"],
      created_by: "finance-manager"
    },
    "http://api.local",
    fetcher
  );
  await downloadAccountingArchivePackage("arch_case_1", "http://api.local", fetcher);

  assert.equal(documents.total, 1);
  assert.equal(archiveCase.archive_case_id, "arch_case_1");
  assert.equal(fetcher.calls.at(-1).url, "http://api.local/api/v1/accounting-archive/cases/arch_case_1/download");
});
```

- [ ] **Step 2: Add frontend types**

Create `frontend/src/types/accountingArchive.ts`:

```typescript
export type ArchiveStatus = "draft" | "indexed" | "archived" | "locked";
export type ArchiveStorageStatus = "metadata_only" | "stored";
export type ArchiveOcrStatus = "not_required" | "text_parsed" | "engine_required" | "failed";
export type ArchiveVerificationStatus = "not_required" | "pending_external" | "verified" | "failed";
export type ArchiveCaseType = "voucher" | "ledger" | "statement" | "mixed";

export interface ArchiveDocument {
  archive_document_id: string;
  account_set_id: string;
  period: string;
  source_type: string;
  source_id: string;
  document_type: string;
  filename: string;
  content_type: string;
  size: number;
  sha256_hash: string;
  storage_status: ArchiveStorageStatus;
  archive_status: ArchiveStatus;
  ocr_status: ArchiveOcrStatus;
  verification_status: ArchiveVerificationStatus;
  retention_years: number;
  uploaded_by: string;
  created_at: string;
}

export interface ArchiveDocumentListResponse {
  total: number;
  documents: ArchiveDocument[];
}

export interface ArchiveCaseCreateRequest {
  account_set_id: string;
  period: string;
  case_type: ArchiveCaseType;
  title: string;
  document_ids: string[];
  created_by: string;
}

export interface ArchiveCase {
  archive_case_id: string;
  account_set_id: string;
  period: string;
  case_type: ArchiveCaseType;
  title: string;
  document_ids: string[];
  document_count: number;
  archive_status: ArchiveStatus;
  retention_years: number;
  created_by: string;
  created_at: string;
}
```

Modify `frontend/src/types/voucherCenter.ts`:

```typescript
export interface VoucherAttachment {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  ocr_status: string;
  archive_document_id?: string | null;
  sha256_hash?: string | null;
  storage_status: string;
}
```

- [ ] **Step 3: Add dashboard API helpers**

In `frontend/src/services/dashboardApi.ts`:

```typescript
import type {
  ArchiveCase,
  ArchiveCaseCreateRequest,
  ArchiveDocumentListResponse
} from "../types/accountingArchive";
```

Add:

```typescript
export function fetchAccountingArchiveDocuments(
  accountSetId = "default",
  period = "",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ArchiveDocumentListResponse> {
  const periodQuery = period ? `&period=${encodeURIComponent(period)}` : "";
  return fetcher(
    `${apiBase}/api/v1/accounting-archive/documents?account_set_id=${encodeURIComponent(accountSetId)}${periodQuery}`,
    { headers: { "X-Actor-Id": actorId } }
  ).then(async (response) => {
    if (!response.ok) {
      throw new Error(`会计档案 API 请求失败：${response.status}`);
    }
    return response.json() as Promise<ArchiveDocumentListResponse>;
  });
}


export function createAccountingArchiveCase(
  request: ArchiveCaseCreateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ArchiveCase> {
  return fetcher(`${apiBase}/api/v1/accounting-archive/cases`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(request)
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`会计档案案卷创建失败：${response.status}`);
    }
    return response.json() as Promise<ArchiveCase>;
  });
}
```

Add download helper:

```typescript
export async function downloadAccountingArchivePackage(
  archiveCaseId: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
) {
  const response = await fetcher(
    `${apiBase}/api/v1/accounting-archive/cases/${encodeURIComponent(archiveCaseId)}/download`,
    { headers: { "X-Actor-Id": actorId } }
  );
  if (!response.ok) {
    throw new Error(`会计档案下载失败：${response.status}`);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? "accounting-archive.zip";
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}
```

- [ ] **Step 4: Build AccountingArchivePanel**

Create `frontend/src/components/AccountingArchivePanel.tsx`:

```tsx
import { useEffect, useMemo, useState } from "react";
import {
  createAccountingArchiveCase,
  downloadAccountingArchivePackage,
  fetchAccountingArchiveDocuments
} from "../services/dashboardApi";
import type { ArchiveDocument } from "../types/accountingArchive";

interface AccountingArchivePanelProps {
  period: string;
}

export default function AccountingArchivePanel({ period }: AccountingArchivePanelProps) {
  const [documents, setDocuments] = useState<ArchiveDocument[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [lastCaseId, setLastCaseId] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedCount = useMemo(() => selectedIds.length, [selectedIds]);

  function refresh() {
    fetchAccountingArchiveDocuments("default", period)
      .then((payload) => setDocuments(payload.documents))
      .catch((archiveError) => {
        setError(archiveError instanceof Error ? archiveError.message : "会计档案读取失败");
      });
  }

  function toggleDocument(documentId: string) {
    setSelectedIds((current) =>
      current.includes(documentId)
        ? current.filter((item) => item !== documentId)
        : [...current, documentId]
    );
  }

  async function handleCreateCase() {
    if (selectedIds.length === 0) {
      setError("请先选择要归档的文档。");
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      const archiveCase = await createAccountingArchiveCase({
        account_set_id: "default",
        period,
        case_type: "voucher",
        title: `${period} 凭证档案`,
        document_ids: selectedIds,
        created_by: "finance-manager"
      });
      setLastCaseId(archiveCase.archive_case_id);
    } catch (archiveError) {
      setError(archiveError instanceof Error ? archiveError.message : "会计档案案卷创建失败");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(refresh, [period]);

  return (
    <section id="accounting-archive-panel" className="accounting-archive-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">会计档案</span>
          <h2>电子凭证与档案目录</h2>
        </div>
        <div className="statement-actions">
          <span>{selectedCount} 个文档</span>
          <button type="button" className="button-secondary" onClick={handleCreateCase} disabled={isBusy}>
            创建案卷
          </button>
          <button type="button" onClick={() => lastCaseId && downloadAccountingArchivePackage(lastCaseId)} disabled={!lastCaseId || isBusy}>
            下载归档包
          </button>
        </div>
      </div>
      {error ? <p className="inline-error">{error}</p> : null}
      <div className="voucher-table-wrap">
        <table className="voucher-table accounting-archive-table">
          <thead>
            <tr>
              <th>选择</th>
              <th>文件名</th>
              <th>来源</th>
              <th>OCR</th>
              <th>验真</th>
              <th>保管</th>
              <th>哈希</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((document) => (
              <tr key={document.archive_document_id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(document.archive_document_id)}
                    onChange={() => toggleDocument(document.archive_document_id)}
                    aria-label={`选择 ${document.filename}`}
                  />
                </td>
                <td>{document.filename}</td>
                <td>{document.source_type}</td>
                <td>{document.ocr_status}</td>
                <td>{document.verification_status}</td>
                <td>{document.retention_years}年</td>
                <td>{document.sha256_hash.slice(0, 12)}</td>
              </tr>
            ))}
            {documents.length === 0 ? (
              <tr>
                <td colSpan={7}>当前期间暂无归档文档</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Show archive metadata in voucher panel**

In `frontend/src/components/VoucherCenterPanel.tsx`, update attachment list:

```tsx
{selectedVoucher?.attachments.length ? (
  selectedVoucher.attachments.map((attachment) => (
    <small key={attachment.id}>
      {attachment.filename} · {attachment.ocr_status} · {attachment.storage_status}
      {attachment.sha256_hash ? ` · ${attachment.sha256_hash.slice(0, 12)}` : ""}
    </small>
  ))
) : <p className="muted">暂无附件。</p>}
```

In `frontend/src/components/DashboardLayout.tsx`, render `AccountingArchivePanel` after `VoucherCenterPanel`.

- [ ] **Step 6: Add frontend panel tests**

Create `frontend/tests/accountingArchivePanel.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("会计档案面板展示文档、案卷和下载入口", async () => {
  const panel = await readFile(resolve("src/components/AccountingArchivePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");
  const voucherPanel = await readFile(resolve("src/components/VoucherCenterPanel.tsx"), "utf8");

  assert.match(panel, /accounting-archive-panel/);
  assert.match(panel, /fetchAccountingArchiveDocuments/);
  assert.match(panel, /createAccountingArchiveCase/);
  assert.match(panel, /downloadAccountingArchivePackage/);
  assert.match(layout, /AccountingArchivePanel/);
  assert.match(voucherPanel, /sha256_hash/);
  assert.match(voucherPanel, /storage_status/);
});
```

In `frontend/package.json`, add:

```json
"node tests/accountingArchiveApi.test.mjs && node tests/accountingArchivePanel.test.mjs"
```

to the existing `test:nav` command.

- [ ] **Step 7: Verify and commit**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
git add frontend/src/types/accountingArchive.ts frontend/src/types/voucherCenter.ts frontend/src/services/dashboardApi.ts frontend/src/components/AccountingArchivePanel.tsx frontend/src/components/VoucherCenterPanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/accountingArchiveApi.test.mjs frontend/tests/accountingArchivePanel.test.mjs frontend/tests/voucherCenterPanel.test.mjs frontend/package.json
git commit -m "feat: add accounting archive panel"
```

## Task 6: 文档、回归验证与档案边界

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Document archive workflow**

Update docs with:
- 凭证附件上传后生成档案文档
- 文件哈希、OCR 状态、验真状态和存储状态含义
- 图片/PDF 无 OCR 引擎时的行为
- 发票/回单外部验真未接入时的行为
- 保管期限默认策略
- 档案案卷和归档包下载
- 权限和审计事件

- [ ] **Step 2: Document API changes**

In `docs/02-api-design.md`, add:

```markdown
GET /api/v1/accounting-archive/documents?account_set_id=default&period=2026-06
GET /api/v1/accounting-archive/documents/{archive_document_id}
POST /api/v1/accounting-archive/cases
GET /api/v1/accounting-archive/cases/{archive_case_id}/download
```

Permissions:
- `archive.read`
- `archive.document.create`
- `archive.case.create`
- `archive.package.download`
- `archive.verification.update`

Audit events:
- `archive.document.list`
- `archive.document.get`
- `archive.document.create`
- `archive.case.create`
- `archive.package.download`
- `archive.verification.update`

- [ ] **Step 3: Run backend regression**

```powershell
python -m pytest backend/tests/test_accounting_archive_service.py backend/tests/test_accounting_archive_api.py backend/tests/test_voucher_center_service.py backend/tests/test_voucher_center_permission_api.py backend/tests/test_system_admin_api.py
```

Expected result: all selected backend tests pass.

- [ ] **Step 4: Run frontend regression and build**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: frontend tests and production build pass. Existing Vite chunk-size warnings are acceptable only when the build exits with code 0.

- [ ] **Step 5: Manual verification scenario**

手工验证场景：
1. 在 `default` 账套为 `2026-06` 创建一张凭证。
2. 上传 `invoice.txt` 作为凭证附件。
3. 确认凭证附件展示 `archive_document_id`、`sha256_hash`、`storage_status` 和 OCR 状态。
4. 打开会计档案面板，确认文档出现在 `2026-06` 期间下。
5. 使用上传文档创建凭证档案案卷。
6. 下载归档包，确认 ZIP 包含 `manifest.json`、文档元数据 JSON 和文本摘录。
7. 上传图片或 PDF，确认系统生成 `ocr_status="engine_required"`，且没有伪造 OCR 字段。
8. 确认发票和银行回单文档在接入真实验真服务前使用 `verification_status="pending_external"`。
9. 确认审计日志包含档案文档创建、档案案卷创建和归档包下载事件。

- [ ] **Step 6: Final docs commit**

```powershell
git add README.md docs/01-mvp-design.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "docs: document accounting archive workflow"
```

## Acceptance Criteria

- Voucher attachment upload creates an archive document with stable SHA-256 hash.
- Archive documents include source object, account set, period, document type, OCR status, verification status, storage status and retention years.
- Text attachments can preserve extracted text; images/PDFs without OCR engine are marked `engine_required`.
- Invoice and bank receipt documents are marked `pending_external` unless a real verification integration updates them.
- Archive cases can group documents by account set, period and case type.
- Archive package ZIP includes manifest, document metadata and available text extracts.
- Archive APIs are permission-protected and audited.
- Frontend displays archive documents, hash prefix, OCR/verification status, retention years and package download action.
- Documentation states the archive boundary and explicitly says the MVP does not provide CA signing or official external verification.

## Risk Controls

- Compute SHA-256 from uploaded bytes before discarding content.
- Do not persist binary bytes in SQLite for the MVP.
- Do not fabricate OCR text or verification status.
- Keep archive documents append-only after creation; future corrections create new documents or status events.
- Keep source links explicit through `source_type` and `source_id`.
- Use ZIP manifest as the portable exchange format until real archive storage is introduced.
- Run backend and frontend regression commands before merging implementation work.
