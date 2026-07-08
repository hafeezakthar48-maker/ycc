# Formal Accounting Engine Phase 6 Statement Export Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在正式报表映射基础上，建立财务报表快照、版本锁定、Excel/PDF 导出、归档审计和期间关闭后的重生成策略。
**Architecture:** 报表导出必须基于可追溯的 `statement_snapshot`，而不是每次下载时临时重算。后端新增快照归档服务和报表导出服务，快照保存报表包 JSON、映射集、校验结果、内容哈希、版本号和锁定状态；导出服务从快照渲染 Excel/PDF；前端在财务报表面板中增加快照列表、锁定、归档和下载入口。
**Tech Stack:** FastAPI、Pydantic、SQLite、Decimal、hashlib、zipfile、pytest、React、TypeScript、Vite、Node test runner。
---

## Prerequisite

必须先完成并验证：
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-1.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-4-period-close.md`
- `docs/superpowers/plans/2026-07-06-formal-accounting-engine-phase-5-statement-mapping.md`
- 后端 `FinancialStatementBundle` 已包含 `mapping_set_id`、`trace_items` 和 `validation_items`
- 后端已有 `POST /api/v1/financial-statements/generate`
- 后端已有管理报告 `DOCX/PDF` 导出模式可参考，但正式财务报表导出需要独立服务
- 前端已有 `FinancialStatementPanel` 展示报表

本期不做电子会计档案长期存储介质适配、CA 签章、XBRL、税局申报文件、对象存储、加密归档、跨账套合并归档。本期先实现本地 SQLite 元数据和内存/文件字节生成能力，让正式报表具备可下载、可锁定、可审计、可复核的最小闭环。

## Accounting Decisions

- 报表快照是正式报表归档的最小版本单元，导出文件必须引用一个 `snapshot_id`。
- 同一账套、同一期间可以存在多个快照版本，版本号按创建顺序递增。
- 快照内容哈希使用规范化 JSON 计算，确保同一报表内容得到稳定 `content_hash`。
- 锁定快照后，快照 JSON、映射集、校验结果和导出文件名不能被修改。
- 关闭期间允许重新生成新的报表快照，但不能覆盖已锁定版本；新快照必须拥有新的版本号和审计记录。
- 导出 Excel 文件包含四张标准报表、校验结果和追溯明细工作表。
- 导出 PDF 文件包含封面、四张报表摘要、校验结果和快照元数据。
- 有失败校验项的快照可以导出，但文件和 API 响应必须标记 `validation_status="failed"`。
- 样例数据回退生成的快照可以导出，但不能标记为正式归档，只能标记为 `archive_status="demo_only"`。

## File Structure

- Create: `backend/app/models/statement_archive.py`
  - 定义报表快照、归档状态、导出格式、导出记录、锁定请求和响应模型。
- Create: `backend/app/services/statement_archive_service.py`
  - 创建快照、计算哈希、递增版本、锁定快照、查询快照和记录导出审计。
- Create: `backend/app/services/statement_export_service.py`
  - 从快照生成 Excel 和 PDF 字节，提供文件名和 MIME 类型。
- Modify: `backend/app/api/financial_statements.py`
  - 增加快照创建、列表、详情、锁定、归档和导出 API。
- Modify: `backend/app/services/system_admin_service.py`
  - 增加 `statement.snapshot.create`、`statement.snapshot.lock`、`statement.archive.view`、`statement.export` 权限。
- Modify: `backend/app/services/module_registry_service.py`
  - 注册快照、归档、导出 API 前缀和审计事件。
- Create: `backend/tests/test_statement_archive_service.py`
- Create: `backend/tests/test_statement_export_service.py`
- Modify: `backend/tests/test_financial_statement_api.py`
- Modify: `backend/tests/test_system_admin_api.py`
- Create: `frontend/src/types/statementArchive.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/StatementArchivePanel.tsx`
- Modify: `frontend/src/components/FinancialStatementPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/statementArchiveApi.test.mjs`
- Create: `frontend/tests/statementArchivePanel.test.mjs`
- Modify: `frontend/tests/financialStatementPanel.test.mjs`
- Modify: `frontend/package.json`
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

## Task 1: 报表快照模型与版本服务

**Files:**
- Create: `backend/app/models/statement_archive.py`
- Create: `backend/app/services/statement_archive_service.py`
- Create: `backend/tests/test_statement_archive_service.py`

- [ ] **Step 1: Write failing snapshot service tests**

Create `backend/tests/test_statement_archive_service.py`:

```python
from app.models.financial_statement import FinancialStatementGenerateRequest
from app.services.financial_statement_service import generate_financial_statements
from app.services.statement_archive_service import (
    create_statement_snapshot,
    get_statement_snapshot,
    list_statement_snapshots,
    reset_statement_archive_store,
)


def setup_function():
    reset_statement_archive_store()


def test_create_statement_snapshot_assigns_version_and_hash():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))

    first = create_statement_snapshot(bundle=bundle, created_by="finance-user")
    second = create_statement_snapshot(bundle=bundle, created_by="finance-user")
    loaded = get_statement_snapshot(first.snapshot_id)
    listed = list_statement_snapshots(account_set_id="default", period="2026-06")

    assert first.version == 1
    assert second.version == 2
    assert first.content_hash == second.content_hash
    assert loaded.snapshot_id == first.snapshot_id
    assert listed.total == 2
    assert listed.items[0].version == 2
```

- [ ] **Step 2: Implement snapshot models**

Create `backend/app/models/statement_archive.py`:

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.financial_statement import FinancialStatementBundle


StatementArchiveStatus = Literal["draft", "locked", "archived", "demo_only"]
StatementValidationStatus = Literal["passed", "warning", "failed"]
StatementExportFormat = Literal["xlsx", "pdf"]


class StatementSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    account_set_id: str
    period: str
    company_name: str
    version: int
    mapping_set_id: str
    source: str
    content_hash: str
    validation_status: StatementValidationStatus
    archive_status: StatementArchiveStatus
    locked: bool = False
    created_by: str
    created_at: str
    locked_by: str | None = None
    locked_at: str | None = None
    bundle: FinancialStatementBundle


class StatementSnapshotListResponse(BaseModel):
    total: int
    items: list[StatementSnapshot]


class StatementSnapshotCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    account_set_id: str = "default"
    operator: str = "财务主管"
    created_by: str = "finance-user"


class StatementSnapshotLockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locked_by: str = Field(min_length=1, max_length=64)


class StatementExportRecord(BaseModel):
    export_id: str
    snapshot_id: str
    export_format: StatementExportFormat
    filename: str
    content_type: str
    exported_by: str
    exported_at: str
```

- [ ] **Step 3: Implement in-memory archive service**

Create `backend/app/services/statement_archive_service.py`:

```python
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.models.financial_statement import FinancialStatementBundle
from app.models.statement_archive import (
    StatementExportRecord,
    StatementSnapshot,
    StatementSnapshotListResponse,
)

_STATEMENT_SNAPSHOTS: dict[str, StatementSnapshot] = {}
_STATEMENT_EXPORTS: dict[str, StatementExportRecord] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_statement_archive_store() -> None:
    _STATEMENT_SNAPSHOTS.clear()
    _STATEMENT_EXPORTS.clear()


def create_statement_snapshot(bundle: FinancialStatementBundle, created_by: str) -> StatementSnapshot:
    version = _next_version(bundle.account_set_id, bundle.period)
    snapshot = StatementSnapshot(
        snapshot_id=f"stmt_snap_{uuid4().hex}",
        account_set_id=bundle.account_set_id,
        period=bundle.period,
        company_name=bundle.company_name,
        version=version,
        mapping_set_id=getattr(bundle, "mapping_set_id", "legacy"),
        source=bundle.source,
        content_hash=statement_bundle_hash(bundle),
        validation_status=_validation_status(bundle),
        archive_status="demo_only" if bundle.source == "sample_finance_data" else "draft",
        created_by=created_by,
        created_at=_now_iso(),
        bundle=bundle,
    )
    _STATEMENT_SNAPSHOTS[snapshot.snapshot_id] = snapshot
    return snapshot


def get_statement_snapshot(snapshot_id: str) -> StatementSnapshot:
    snapshot = _STATEMENT_SNAPSHOTS.get(snapshot_id)
    if snapshot is None:
        raise ValueError(f"未找到报表快照 {snapshot_id}")
    return snapshot


def list_statement_snapshots(account_set_id: str, period: str | None = None) -> StatementSnapshotListResponse:
    items = [
        snapshot for snapshot in _STATEMENT_SNAPSHOTS.values()
        if snapshot.account_set_id == account_set_id and (period is None or snapshot.period == period)
    ]
    items.sort(key=lambda item: (item.period, item.version), reverse=True)
    return StatementSnapshotListResponse(total=len(items), items=items)


def statement_bundle_hash(bundle: FinancialStatementBundle) -> str:
    payload = bundle.model_dump(mode="json")
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _next_version(account_set_id: str, period: str) -> int:
    versions = [
        snapshot.version for snapshot in _STATEMENT_SNAPSHOTS.values()
        if snapshot.account_set_id == account_set_id and snapshot.period == period
    ]
    return max(versions, default=0) + 1


def _validation_status(bundle: FinancialStatementBundle) -> str:
    validation_items = getattr(bundle, "validation_items", [])
    if any(item.status == "failed" for item in validation_items):
        return "failed"
    if any(item.status == "warning" for item in validation_items):
        return "warning"
    return "passed"
```

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_statement_archive_service.py
git add backend/app/models/statement_archive.py backend/app/services/statement_archive_service.py backend/tests/test_statement_archive_service.py
git commit -m "feat: add statement snapshots"
```

## Task 2: 快照锁定、归档状态与导出记录

**Files:**
- Modify: `backend/app/services/statement_archive_service.py`
- Modify: `backend/tests/test_statement_archive_service.py`

- [ ] **Step 1: Write failing lock and export record tests**

Append to `backend/tests/test_statement_archive_service.py`:

```python
from app.services.statement_archive_service import (
    lock_statement_snapshot,
    record_statement_export,
)


def test_lock_statement_snapshot_marks_archived_when_formal_source():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))
    snapshot = create_statement_snapshot(bundle=bundle, created_by="finance-user")

    locked = lock_statement_snapshot(snapshot.snapshot_id, locked_by="finance-manager")

    assert locked.locked is True
    assert locked.locked_by == "finance-manager"
    assert locked.archive_status in {"archived", "demo_only"}


def test_record_statement_export_keeps_snapshot_reference():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))
    snapshot = create_statement_snapshot(bundle=bundle, created_by="finance-user")

    export = record_statement_export(
        snapshot_id=snapshot.snapshot_id,
        export_format="xlsx",
        filename="financial-statements-default-2026-06-v1.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        exported_by="finance-user",
    )

    assert export.snapshot_id == snapshot.snapshot_id
    assert export.export_format == "xlsx"
    assert export.filename.endswith(".xlsx")
```

- [ ] **Step 2: Implement lock and export record functions**

In `backend/app/services/statement_archive_service.py`:

```python
def lock_statement_snapshot(snapshot_id: str, locked_by: str) -> StatementSnapshot:
    snapshot = get_statement_snapshot(snapshot_id)
    if snapshot.locked:
        return snapshot
    now = _now_iso()
    archive_status = "demo_only" if snapshot.source == "sample_finance_data" else "archived"
    locked = snapshot.model_copy(
        update={
            "locked": True,
            "locked_by": locked_by,
            "locked_at": now,
            "archive_status": archive_status,
        }
    )
    _STATEMENT_SNAPSHOTS[snapshot_id] = locked
    return locked


def record_statement_export(
    snapshot_id: str,
    export_format: str,
    filename: str,
    content_type: str,
    exported_by: str,
) -> StatementExportRecord:
    get_statement_snapshot(snapshot_id)
    export = StatementExportRecord(
        export_id=f"stmt_export_{uuid4().hex}",
        snapshot_id=snapshot_id,
        export_format=export_format,
        filename=filename,
        content_type=content_type,
        exported_by=exported_by,
        exported_at=_now_iso(),
    )
    _STATEMENT_EXPORTS[export.export_id] = export
    return export
```

- [ ] **Step 3: Verify and commit**

```powershell
python -m pytest backend/tests/test_statement_archive_service.py
git add backend/app/services/statement_archive_service.py backend/tests/test_statement_archive_service.py
git commit -m "feat: lock statement snapshots"
```

## Task 3: Excel/PDF 导出服务

**Files:**
- Create: `backend/app/services/statement_export_service.py`
- Create: `backend/tests/test_statement_export_service.py`

- [ ] **Step 1: Write failing export service tests**

Create `backend/tests/test_statement_export_service.py`:

```python
from io import BytesIO
from zipfile import ZipFile

from app.models.financial_statement import FinancialStatementGenerateRequest
from app.services.financial_statement_service import generate_financial_statements
from app.services.statement_archive_service import create_statement_snapshot, reset_statement_archive_store
from app.services.statement_export_service import (
    EXCEL_STATEMENT_MIME_TYPE,
    PDF_STATEMENT_MIME_TYPE,
    build_statement_export,
    statement_export_filename,
)


def setup_function():
    reset_statement_archive_store()


def test_build_statement_xlsx_contains_required_worksheets():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))
    snapshot = create_statement_snapshot(bundle=bundle, created_by="finance-user")

    payload = build_statement_export(snapshot, "xlsx")

    assert payload.content_type == EXCEL_STATEMENT_MIME_TYPE
    assert payload.filename == "financial-statements-default-2026-06-v1.xlsx"
    with ZipFile(BytesIO(payload.content)) as workbook:
        workbook_names = set(workbook.namelist())
    assert "xl/workbook.xml" in workbook_names
    assert "xl/worksheets/sheet1.xml" in workbook_names


def test_build_statement_pdf_returns_pdf_bytes():
    bundle = generate_financial_statements(FinancialStatementGenerateRequest(period="2026-06"))
    snapshot = create_statement_snapshot(bundle=bundle, created_by="finance-user")

    payload = build_statement_export(snapshot, "pdf")

    assert payload.content_type == PDF_STATEMENT_MIME_TYPE
    assert payload.filename == statement_export_filename(snapshot, "pdf")
    assert payload.content.startswith(b"%PDF")
```

- [ ] **Step 2: Implement export payload and constants**

Create `backend/app/services/statement_export_service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.models.financial_statement import FinancialStatementBundle, StatementLineItem
from app.models.statement_archive import StatementSnapshot

EXCEL_STATEMENT_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_STATEMENT_MIME_TYPE = "application/pdf"


@dataclass(frozen=True)
class StatementExportPayload:
    filename: str
    content_type: str
    content: bytes


def statement_export_filename(snapshot: StatementSnapshot, export_format: str) -> str:
    return (
        f"financial-statements-{snapshot.account_set_id}-"
        f"{snapshot.period}-v{snapshot.version}.{export_format}"
    )


def build_statement_export(snapshot: StatementSnapshot, export_format: str) -> StatementExportPayload:
    if export_format == "xlsx":
        return StatementExportPayload(
            filename=statement_export_filename(snapshot, "xlsx"),
            content_type=EXCEL_STATEMENT_MIME_TYPE,
            content=build_statement_xlsx(snapshot),
        )
    if export_format == "pdf":
        return StatementExportPayload(
            filename=statement_export_filename(snapshot, "pdf"),
            content_type=PDF_STATEMENT_MIME_TYPE,
            content=build_statement_pdf(snapshot),
        )
    raise ValueError(f"不支持的报表导出格式：{export_format}")
```

- [ ] **Step 3: Implement minimal XLSX writer**

In `backend/app/services/statement_export_service.py`:

```python
def build_statement_xlsx(snapshot: StatementSnapshot) -> bytes:
    output = BytesIO()
    sheets = _statement_sheets(snapshot.bundle)
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _xlsx_content_types(len(sheets)))
        package.writestr("_rels/.rels", _xlsx_root_relationships())
        package.writestr("xl/workbook.xml", _xlsx_workbook(sheets))
        package.writestr("xl/_rels/workbook.xml.rels", _xlsx_workbook_relationships(len(sheets)))
        for index, sheet in enumerate(sheets, start=1):
            package.writestr(f"xl/worksheets/sheet{index}.xml", _xlsx_sheet(sheet["rows"]))
    return output.getvalue()


def _statement_sheets(bundle: FinancialStatementBundle) -> list[dict]:
    return [
        {"name": "资产负债表", "rows": _statement_rows(bundle.balance_sheet.title, bundle.balance_sheet.items)},
        {"name": "利润表", "rows": _statement_rows(bundle.income_statement.title, bundle.income_statement.items)},
        {"name": "现金流量表", "rows": _statement_rows(bundle.cash_flow_statement.title, bundle.cash_flow_statement.items)},
        {"name": "所有者权益变动表", "rows": _statement_rows(bundle.equity_statement.title, bundle.equity_statement.items)},
        {"name": "校验结果", "rows": _validation_rows(bundle)},
        {"name": "追溯明细", "rows": _trace_rows(bundle)},
    ]


def _statement_rows(title: str, items: list[StatementLineItem]) -> list[list[str]]:
    rows = [[title, "", ""], ["项目编码", "项目名称", "金额"]]
    for item in items:
        rows.append([item.code, item.name, str(item.amount)])
    return rows
```

Add XML helpers:

```python
def _xlsx_content_types(sheet_count: int) -> str:
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f"{sheet_overrides}</Types>"
    )


def _xlsx_root_relationships() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )


def _xlsx_workbook(sheets: list[dict]) -> str:
    sheet_xml = "".join(
        f'<sheet name="{escape(sheet["name"])}" sheetId="{index}" r:id="rId{index}"/>'
        for index, sheet in enumerate(sheets, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_xml}</sheets></workbook>"
    )


def _xlsx_workbook_relationships(sheet_count: int) -> str:
    relationships = "".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{relationships}</Relationships>"
    )


def _xlsx_sheet(rows: list[list[str]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{chr(64 + column_index)}{row_index}"
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
    )
```

- [ ] **Step 4: Implement PDF writer**

In `backend/app/services/statement_export_service.py`:

```python
def build_statement_pdf(snapshot: StatementSnapshot) -> bytes:
    lines = _pdf_lines(snapshot)
    content = _pdf_content_stream(lines)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
        b"/Encoding /UniGB-UCS2-H /DescendantFonts [6 0 R] >>",
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream",
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 2 >> "
        b"/FontDescriptor 7 0 R >>",
        b"<< /Type /FontDescriptor /FontName /STSong-Light /Flags 4 "
        b"/FontBBox [-25 -254 1000 880] /ItalicAngle 0 /Ascent 880 "
        b"/Descent -254 /CapHeight 880 /StemV 80 >>",
    ]
    return _assemble_pdf(objects)
```

Add PDF helpers:

```python
def _pdf_lines(snapshot: StatementSnapshot) -> list[tuple[str, int]]:
    bundle = snapshot.bundle
    return [
        ("财务报表", 18),
        (f"企业：{snapshot.company_name}", 11),
        (f"期间：{snapshot.period}", 11),
        (f"账套：{snapshot.account_set_id}", 11),
        (f"版本：v{snapshot.version}", 11),
        (f"内容哈希：{snapshot.content_hash[:16]}", 8),
        ("资产负债表", 13),
        (f"资产合计：{bundle.balance_sheet.total_assets}", 10),
        (f"负债和权益合计：{bundle.balance_sheet.total_liabilities_and_equity}", 10),
        ("利润表", 13),
        (f"营业收入：{bundle.income_statement.total_revenue}", 10),
        (f"净利润：{bundle.income_statement.net_profit}", 10),
        ("现金流量表", 13),
        (f"现金净增加额：{bundle.cash_flow_statement.net_cash_flow}", 10),
        ("所有者权益变动表", 13),
        (f"期末权益：{bundle.equity_statement.closing_equity}", 10),
        ("校验状态", 13),
        (f"{snapshot.validation_status}", 10),
    ]
```

Add PDF assembly helpers:

```python
def _pdf_content_stream(lines: list[tuple[str, int]]) -> bytes:
    commands: list[str] = []
    y = 790
    for text, size in lines:
        if y < 70:
            break
        if not text:
            y -= 10
            continue
        encoded = text.encode("utf-16-be").hex().upper()
        commands.append(f"BT /F1 {size} Tf 52 {y} Td <{encoded}> Tj ET")
        y -= size + 8
    return "\n".join(commands).encode("ascii")


def _assemble_pdf(objects: list[bytes]) -> bytes:
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, payload in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(payload)
        output.write(b"\nendobj\n")

    xref_position = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF".encode("ascii")
    )
    return output.getvalue()
```

- [ ] **Step 5: Add validation and trace sheet helpers**

In `backend/app/services/statement_export_service.py`:

```python
def _validation_rows(bundle: FinancialStatementBundle) -> list[list[str]]:
    rows = [["校验编码", "校验名称", "状态", "说明"]]
    for item in getattr(bundle, "validation_items", []):
        rows.append([item.validation_code, item.validation_name, item.status, item.message])
    if len(rows) == 1:
        rows.append(["none", "校验结果", "passed", "当前报表无结构化校验项"])
    return rows


def _trace_rows(bundle: FinancialStatementBundle) -> list[list[str]]:
    rows = [["项目编码", "规则", "来源", "科目", "公式", "金额"]]
    for item in getattr(bundle, "trace_items", []):
        rows.append(
            [
                item.line_code,
                item.rule_id,
                item.source_type,
                " / ".join(item.source_account_codes),
                item.formula,
                str(item.amount),
            ]
        )
    if len(rows) == 1:
        rows.append(["none", "legacy", "formula", "", "当前报表无追溯明细", "0.00"])
    return rows
```

- [ ] **Step 6: Verify and commit**

```powershell
python -m pytest backend/tests/test_statement_export_service.py
git add backend/app/services/statement_export_service.py backend/tests/test_statement_export_service.py
git commit -m "feat: export statement snapshots"
```

## Task 4: 快照与导出 API、权限和审计

**Files:**
- Modify: `backend/app/api/financial_statements.py`
- Modify: `backend/app/services/system_admin_service.py`
- Modify: `backend/app/services/module_registry_service.py`
- Modify: `backend/tests/test_financial_statement_api.py`
- Modify: `backend/tests/test_system_admin_api.py`

- [ ] **Step 1: Write failing API tests**

Append to `backend/tests/test_financial_statement_api.py`:

```python
def test_create_lock_and_export_statement_snapshot():
    create_response = client.post(
        "/api/v1/financial-statements/snapshots",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"period": "2026-06", "account_set_id": "default", "created_by": "finance-user"},
    )

    assert create_response.status_code == 200
    snapshot = create_response.json()
    assert snapshot["period"] == "2026-06"
    assert snapshot["version"] == 1
    assert snapshot["content_hash"]

    lock_response = client.post(
        f"/api/v1/financial-statements/snapshots/{snapshot['snapshot_id']}/lock",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"locked_by": "finance-manager"},
    )

    assert lock_response.status_code == 200
    assert lock_response.json()["locked"] is True

    export_response = client.get(
        f"/api/v1/financial-statements/snapshots/{snapshot['snapshot_id']}/export/xlsx",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "financial-statements-default-2026-06-v1.xlsx" in export_response.headers["content-disposition"]


def test_list_statement_snapshots_returns_versions():
    client.post(
        "/api/v1/financial-statements/snapshots",
        headers={"X-Actor-Id": "u-finance-manager"},
        json={"period": "2026-06", "account_set_id": "default", "created_by": "finance-user"},
    )

    response = client.get(
        "/api/v1/financial-statements/snapshots?account_set_id=default&period=2026-06",
        headers={"X-Actor-Id": "u-finance-manager"},
    )

    assert response.status_code == 200
    assert response.json()["total"] >= 1
```

- [ ] **Step 2: Add API routes**

In `backend/app/api/financial_statements.py`:

```python
from fastapi import Response

from app.models.statement_archive import StatementSnapshotCreateRequest, StatementSnapshotLockRequest
from app.services.statement_archive_service import (
    create_statement_snapshot,
    get_statement_snapshot,
    list_statement_snapshots,
    lock_statement_snapshot,
    record_statement_export,
)
from app.services.statement_export_service import build_statement_export
```

Add routes:

```python
@router.post("/snapshots")
def create_snapshot(request: StatementSnapshotCreateRequest, x_actor_id: str = Header(default="system")):
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.snapshot.create",
        event="statement.snapshot.create",
        target_id=f"statement-snapshot:{request.account_set_id}:{request.period}",
        metadata={"account_set_id": request.account_set_id, "period": request.period},
    )
    bundle = generate_financial_statements(
        FinancialStatementGenerateRequest(
            period=request.period,
            account_set_id=request.account_set_id,
            operator=request.operator,
        )
    )
    snapshot = create_statement_snapshot(bundle=bundle, created_by=request.created_by)
    _record_statement_audit(
        actor_id=x_actor_id,
        event="statement.snapshot.create",
        target_id=snapshot.snapshot_id,
        metadata={"period": snapshot.period, "version": snapshot.version, "content_hash": snapshot.content_hash},
    )
    return snapshot


@router.get("/snapshots")
def list_snapshots(account_set_id: str = "default", period: str | None = None, x_actor_id: str = Header(default="system")):
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.archive.view",
        event="statement.archive.view",
        target_id=f"statement-archive:{account_set_id}:{period or 'all'}",
        metadata={"account_set_id": account_set_id, "period": period or ""},
    )
    return list_statement_snapshots(account_set_id=account_set_id, period=period)
```

Add lock/export routes:

```python
@router.post("/snapshots/{snapshot_id}/lock")
def lock_snapshot(snapshot_id: str, request: StatementSnapshotLockRequest, x_actor_id: str = Header(default="system")):
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.snapshot.lock",
        event="statement.snapshot.lock",
        target_id=snapshot_id,
        metadata={"snapshot_id": snapshot_id, "locked_by": request.locked_by},
    )
    snapshot = lock_statement_snapshot(snapshot_id, locked_by=request.locked_by)
    _record_statement_audit(
        actor_id=x_actor_id,
        event="statement.snapshot.lock",
        target_id=snapshot.snapshot_id,
        metadata={"period": snapshot.period, "version": snapshot.version},
    )
    return snapshot


@router.get("/snapshots/{snapshot_id}/export/{export_format}")
def export_snapshot(snapshot_id: str, export_format: str, x_actor_id: str = Header(default="system")):
    _require_permission(
        actor_id=x_actor_id,
        permission_code="statement.export",
        event="statement.export",
        target_id=snapshot_id,
        metadata={"snapshot_id": snapshot_id, "format": export_format},
    )
    snapshot = get_statement_snapshot(snapshot_id)
    payload = build_statement_export(snapshot, export_format)
    record_statement_export(
        snapshot_id=snapshot_id,
        export_format=export_format,
        filename=payload.filename,
        content_type=payload.content_type,
        exported_by=x_actor_id,
    )
    _record_statement_audit(
        actor_id=x_actor_id,
        event="statement.export",
        target_id=snapshot_id,
        metadata={"format": export_format, "filename": payload.filename},
    )
    return Response(
        content=payload.content,
        media_type=payload.content_type,
        headers={"Content-Disposition": f'attachment; filename="{payload.filename}"'},
    )
```

- [ ] **Step 3: Register permissions and module events**

In `backend/app/services/system_admin_service.py`, add:

```python
Permission(
    code="statement.snapshot.create",
    name="创建报表快照",
    module_id="finance-center",
    action="create",
    description="生成并保存财务报表快照。",
),
Permission(
    code="statement.snapshot.lock",
    name="锁定报表快照",
    module_id="finance-center",
    action="lock",
    description="锁定财务报表快照用于归档。",
),
Permission(
    code="statement.archive.view",
    name="查看报表归档",
    module_id="finance-center",
    action="read",
    description="查看财务报表快照和归档版本。",
),
Permission(
    code="statement.export",
    name="导出财务报表",
    module_id="finance-center",
    action="export",
    description="导出财务报表 Excel 或 PDF 文件。",
),
```

Add these permissions to finance manager role.

In `backend/app/services/module_registry_service.py`, add audit events:
- `statement.snapshot.create`
- `statement.snapshot.lock`
- `statement.archive.view`
- `statement.export`

- [ ] **Step 4: Verify and commit**

```powershell
python -m pytest backend/tests/test_financial_statement_api.py backend/tests/test_system_admin_api.py backend/tests/test_statement_archive_service.py backend/tests/test_statement_export_service.py
git add backend/app/api/financial_statements.py backend/app/services/system_admin_service.py backend/app/services/module_registry_service.py backend/tests/test_financial_statement_api.py backend/tests/test_system_admin_api.py
git commit -m "feat: expose statement archive api"
```

## Task 5: 前端快照、锁定与下载入口

**Files:**
- Create: `frontend/src/types/statementArchive.ts`
- Modify: `frontend/src/services/dashboardApi.ts`
- Create: `frontend/src/components/StatementArchivePanel.tsx`
- Modify: `frontend/src/components/FinancialStatementPanel.tsx`
- Modify: `frontend/src/components/DashboardLayout.tsx`
- Create: `frontend/tests/statementArchiveApi.test.mjs`
- Create: `frontend/tests/statementArchivePanel.test.mjs`
- Modify: `frontend/tests/financialStatementPanel.test.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: Write frontend API tests**

Create `frontend/tests/statementArchiveApi.test.mjs`:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import {
  createStatementSnapshot,
  exportStatementSnapshot,
  listStatementSnapshots,
  lockStatementSnapshot
} from "../src/services/dashboardApi.ts";

function createFetcher(payloads) {
  const calls = [];
  const fetcher = async (url, init = {}) => {
    calls.push({ url, init });
    const payload = payloads[url] ?? payloads.default;
    return {
      ok: true,
      status: 200,
      headers: new Map([["content-disposition", 'attachment; filename="financial-statements-default-2026-06-v1.xlsx"']]),
      json: async () => payload,
      blob: async () => new Blob(["xlsx"])
    };
  };
  fetcher.calls = calls;
  return fetcher;
}

test("报表快照 API helper 创建、锁定、列表和导出", async () => {
  const fetcher = createFetcher({
    "http://api.local/api/v1/financial-statements/snapshots": {
      snapshot_id: "stmt_snap_1",
      period: "2026-06",
      version: 1,
      locked: false
    },
    "http://api.local/api/v1/financial-statements/snapshots?account_set_id=default&period=2026-06": {
      total: 1,
      items: [{ snapshot_id: "stmt_snap_1", period: "2026-06", version: 1 }]
    },
    "http://api.local/api/v1/financial-statements/snapshots/stmt_snap_1/lock": {
      snapshot_id: "stmt_snap_1",
      locked: true
    },
    default: {}
  });

  const snapshot = await createStatementSnapshot({ period: "2026-06", account_set_id: "default" }, "http://api.local", fetcher);
  const list = await listStatementSnapshots("default", "2026-06", "http://api.local", fetcher);
  const locked = await lockStatementSnapshot("stmt_snap_1", { locked_by: "finance-manager" }, "http://api.local", fetcher);
  await exportStatementSnapshot("stmt_snap_1", "xlsx", "http://api.local", fetcher);

  assert.equal(snapshot.snapshot_id, "stmt_snap_1");
  assert.equal(list.total, 1);
  assert.equal(locked.locked, true);
  assert.equal(fetcher.calls.at(-1).url, "http://api.local/api/v1/financial-statements/snapshots/stmt_snap_1/export/xlsx");
});
```

- [ ] **Step 2: Add frontend types**

Create `frontend/src/types/statementArchive.ts`:

```typescript
import type { FinancialStatementBundle } from "./financialStatement";

export type StatementArchiveStatus = "draft" | "locked" | "archived" | "demo_only";
export type StatementValidationStatus = "passed" | "warning" | "failed";
export type StatementExportFormat = "xlsx" | "pdf";

export interface StatementSnapshot {
  snapshot_id: string;
  account_set_id: string;
  period: string;
  company_name: string;
  version: number;
  mapping_set_id: string;
  source: string;
  content_hash: string;
  validation_status: StatementValidationStatus;
  archive_status: StatementArchiveStatus;
  locked: boolean;
  created_by: string;
  created_at: string;
  locked_by?: string | null;
  locked_at?: string | null;
  bundle: FinancialStatementBundle;
}

export interface StatementSnapshotListResponse {
  total: number;
  items: StatementSnapshot[];
}

export interface StatementSnapshotCreateRequest {
  period: string;
  account_set_id?: string;
  operator?: string;
  created_by?: string;
}

export interface StatementSnapshotLockRequest {
  locked_by: string;
}
```

- [ ] **Step 3: Add dashboard API helpers**

In `frontend/src/services/dashboardApi.ts`:

```typescript
import type {
  StatementExportFormat,
  StatementSnapshot,
  StatementSnapshotCreateRequest,
  StatementSnapshotListResponse,
  StatementSnapshotLockRequest
} from "../types/statementArchive";
```

Add:

```typescript
export function createStatementSnapshot(
  request: StatementSnapshotCreateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<StatementSnapshot> {
  return mutateFinancialStatementJson<StatementSnapshot>(
    "/api/v1/financial-statements/snapshots",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function listStatementSnapshots(
  accountSetId = "default",
  period = "",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<StatementSnapshotListResponse> {
  const periodQuery = period ? `&period=${encodeURIComponent(period)}` : "";
  return fetcher(
    `${apiBase}/api/v1/financial-statements/snapshots?account_set_id=${encodeURIComponent(accountSetId)}${periodQuery}`,
    { headers: { "X-Actor-Id": actorId } }
  ).then(async (response) => {
    if (!response.ok) {
      throw new Error(`报表归档 API 请求失败：${response.status}`);
    }
    return response.json() as Promise<StatementSnapshotListResponse>;
  });
}

export function lockStatementSnapshot(
  snapshotId: string,
  request: StatementSnapshotLockRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<StatementSnapshot> {
  return mutateFinancialStatementJson<StatementSnapshot>(
    `/api/v1/financial-statements/snapshots/${encodeURIComponent(snapshotId)}/lock`,
    request,
    apiBase,
    fetcher,
    actorId
  );
}
```

Add export helper:

```typescript
export async function exportStatementSnapshot(
  snapshotId: string,
  format: StatementExportFormat,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
) {
  const response = await fetcher(
    `${apiBase}/api/v1/financial-statements/snapshots/${encodeURIComponent(snapshotId)}/export/${format}`,
    { headers: { "X-Actor-Id": actorId } }
  );
  if (!response.ok) {
    throw new Error(`报表导出失败：${response.status}`);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? `financial-statements.${format}`;
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

- [ ] **Step 4: Build StatementArchivePanel**

Create `frontend/src/components/StatementArchivePanel.tsx`:

```tsx
import { useEffect, useState } from "react";
import {
  createStatementSnapshot,
  exportStatementSnapshot,
  listStatementSnapshots,
  lockStatementSnapshot
} from "../services/dashboardApi";
import type { StatementSnapshot } from "../types/statementArchive";

interface StatementArchivePanelProps {
  period: string;
}

export default function StatementArchivePanel({ period }: StatementArchivePanelProps) {
  const [snapshots, setSnapshots] = useState<StatementSnapshot[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    listStatementSnapshots("default", period)
      .then((payload) => setSnapshots(payload.items))
      .catch((archiveError) => {
        setError(archiveError instanceof Error ? archiveError.message : "报表归档读取失败");
      });
  }

  async function handleCreateSnapshot() {
    setIsBusy(true);
    setError(null);
    try {
      await createStatementSnapshot({ period, account_set_id: "default", created_by: "finance-user" });
      refresh();
    } catch (archiveError) {
      setError(archiveError instanceof Error ? archiveError.message : "报表快照创建失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleLock(snapshotId: string) {
    setIsBusy(true);
    setError(null);
    try {
      await lockStatementSnapshot(snapshotId, { locked_by: "finance-manager" });
      refresh();
    } catch (archiveError) {
      setError(archiveError instanceof Error ? archiveError.message : "报表快照锁定失败");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(refresh, [period]);

  return (
    <section id="statement-archive-panel" className="statement-archive-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">报表归档</span>
          <h2>快照、锁定与导出</h2>
        </div>
        <button type="button" onClick={handleCreateSnapshot} disabled={isBusy}>
          {isBusy ? "处理中" : "生成快照"}
        </button>
      </div>
      {error ? <p className="inline-error">{error}</p> : null}
      <div className="voucher-table-wrap">
        <table className="voucher-table statement-archive-table">
          <thead>
            <tr>
              <th>版本</th>
              <th>期间</th>
              <th>状态</th>
              <th>校验</th>
              <th>哈希</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {snapshots.map((snapshot) => (
              <tr key={snapshot.snapshot_id}>
                <td>v{snapshot.version}</td>
                <td>{snapshot.period}</td>
                <td>{snapshot.archive_status}</td>
                <td>{snapshot.validation_status}</td>
                <td>{snapshot.content_hash.slice(0, 12)}</td>
                <td>
                  <button type="button" className="button-secondary" onClick={() => handleLock(snapshot.snapshot_id)} disabled={snapshot.locked || isBusy}>
                    {snapshot.locked ? "已锁定" : "锁定"}
                  </button>
                  <button type="button" className="button-secondary" onClick={() => exportStatementSnapshot(snapshot.snapshot_id, "xlsx")} disabled={isBusy}>
                    Excel
                  </button>
                  <button type="button" className="button-secondary" onClick={() => exportStatementSnapshot(snapshot.snapshot_id, "pdf")} disabled={isBusy}>
                    PDF
                  </button>
                </td>
              </tr>
            ))}
            {snapshots.length === 0 ? (
              <tr>
                <td colSpan={6}>当前期间暂无报表快照</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Wire panel and tests**

Create `frontend/tests/statementArchivePanel.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import test from "node:test";

test("报表归档面板提供快照锁定和下载入口", async () => {
  const panel = await readFile(resolve("src/components/StatementArchivePanel.tsx"), "utf8");
  const layout = await readFile(resolve("src/components/DashboardLayout.tsx"), "utf8");

  assert.match(panel, /statement-archive-panel/);
  assert.match(panel, /createStatementSnapshot/);
  assert.match(panel, /lockStatementSnapshot/);
  assert.match(panel, /exportStatementSnapshot/);
  assert.match(panel, /Excel/);
  assert.match(panel, /PDF/);
  assert.match(layout, /StatementArchivePanel/);
});
```

In `frontend/src/components/DashboardLayout.tsx`, render `StatementArchivePanel` directly after `FinancialStatementPanel`.

In `frontend/package.json`, add:

```json
"node tests/statementArchiveApi.test.mjs && node tests/statementArchivePanel.test.mjs"
```

to the existing `test:nav` command.

- [ ] **Step 6: Verify and commit**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
git add frontend/src/types/statementArchive.ts frontend/src/services/dashboardApi.ts frontend/src/components/StatementArchivePanel.tsx frontend/src/components/FinancialStatementPanel.tsx frontend/src/components/DashboardLayout.tsx frontend/tests/statementArchiveApi.test.mjs frontend/tests/statementArchivePanel.test.mjs frontend/tests/financialStatementPanel.test.mjs frontend/package.json
git commit -m "feat: add statement archive panel"
```

## Task 6: 文档、回归验证与归档策略

**Files:**
- Modify: `README.md`
- Modify: `docs/01-mvp-design.md`
- Modify: `docs/02-api-design.md`
- Modify: `docs/03-frd-v1.0.md`

- [ ] **Step 1: Document statement export and archive workflow**

Update docs with:
- 报表生成、快照创建、锁定、导出、归档的操作顺序
- 快照版本号和内容哈希定义
- Excel 导出工作表范围
- PDF 导出内容范围
- 已关闭期间的重生成策略
- 样例数据快照的 `demo_only` 限制
- 权限和审计事件

- [ ] **Step 2: Document API changes**

In `docs/02-api-design.md`, add:

```markdown
POST /api/v1/financial-statements/snapshots
GET /api/v1/financial-statements/snapshots?account_set_id=default&period=2026-06
POST /api/v1/financial-statements/snapshots/{snapshot_id}/lock
GET /api/v1/financial-statements/snapshots/{snapshot_id}/export/xlsx
GET /api/v1/financial-statements/snapshots/{snapshot_id}/export/pdf
```

Permissions:
- `statement.snapshot.create`
- `statement.snapshot.lock`
- `statement.archive.view`
- `statement.export`

Audit events:
- `statement.snapshot.create`
- `statement.snapshot.lock`
- `statement.archive.view`
- `statement.export`

- [ ] **Step 3: Run backend regression**

```powershell
python -m pytest backend/tests/test_statement_archive_service.py backend/tests/test_statement_export_service.py backend/tests/test_financial_statement_api.py backend/tests/test_financial_statement_service.py backend/tests/test_system_admin_api.py
```

Expected result: all selected backend tests pass.

- [ ] **Step 4: Run frontend regression and build**

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

Expected result: frontend tests and production build pass. Existing Vite chunk-size warnings are acceptable only when the build exits with code 0.

- [ ] **Step 5: Manual verification scenario**

Manual scenario:
1. Generate financial statements for `2026-06`.
2. Create statement snapshot for account set `default`.
3. Confirm snapshot version is `1` and `content_hash` is present.
4. Create a second snapshot and confirm version is `2`.
5. Lock version `1` and confirm archive status is `archived` or `demo_only`.
6. Export version `1` as Excel and confirm workbook opens with four statement sheets plus validation and trace sheets.
7. Export version `1` as PDF and confirm file starts with `%PDF`.
8. List snapshots in frontend and confirm lock/export buttons are visible without table overflow on desktop and mobile.
9. Confirm audit logs include snapshot create, lock and export events.

- [ ] **Step 6: Final docs commit**

```powershell
git add README.md docs/01-mvp-design.md docs/02-api-design.md docs/03-frd-v1.0.md
git commit -m "docs: document statement archive workflow"
```

## Acceptance Criteria

- Statement snapshots are created from `FinancialStatementBundle` with stable `content_hash`.
- Same account set and period can have multiple monotonically increasing snapshot versions.
- Locked snapshots cannot be modified and can be used as archived report versions.
- Sample-data snapshots are marked `demo_only`.
- Excel export includes balance sheet, income statement, cash flow statement, equity statement, validation results and trace details.
- PDF export includes company, period, version, hash, statement summaries and validation status.
- Export APIs return correct `Content-Disposition` and MIME types.
- Snapshot create, lock, archive view and export operations are permission-protected and audited.
- Frontend exposes create snapshot, lock, Excel export and PDF export actions.
- Documentation explains closed-period regeneration and archived snapshot behavior.

## Risk Controls

- Compute hashes from sorted JSON rather than raw Python object order.
- Do not overwrite existing snapshots; create new versions for regenerated statements.
- Keep export generation read-only and side-effect free except export audit records.
- Keep PDF writer small and deterministic; use existing internal PDF assembly pattern.
- Keep Excel writer simple and dependency-light through zipped OpenXML parts.
- Never mark sample-data fallback as formal archive.
- Run backend and frontend regression commands before merging implementation work.
