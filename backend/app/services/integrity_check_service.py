from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.models.accounting import JournalEntryRecord
from app.models.accounting_archive import ArchiveDocument
from app.models.accounting_governance import AccountingIntegrityCheck, AccountingIntegrityReport, CheckStatus
from app.services.accounting_archive_service import list_archive_documents
from app.services.accounting_period_service import is_accounting_period_closed, validate_account_set
from app.services.accounting_service import list_journal_entries
from app.services.statement_mapping_service import get_default_statement_mapping_set, list_statement_mapping_rules


ZERO = Decimal("0.00")


def run_accounting_integrity_checks(account_set_id: str = "default", period: str = "2026-06") -> AccountingIntegrityReport:
    validate_account_set(account_set_id)
    entries = list_journal_entries(account_set_id=account_set_id, period=period).entries
    checks = [
        _check_journal_entries_balanced(entries),
        _check_duplicate_source_keys(entries),
        _check_closed_period_unapproved_entries(account_set_id, period, entries),
        _check_statement_mapping_coverage(account_set_id),
        _check_attachment_archive_links(account_set_id, period, entries),
    ]
    return AccountingIntegrityReport(
        account_set_id=account_set_id,
        period=period,
        overall_status=_overall_status(checks),
        generated_at=_now_iso(),
        checks=checks,
    )


def _check_journal_entries_balanced(entries: list[JournalEntryRecord]) -> AccountingIntegrityCheck:
    unbalanced_entries: list[str] = []
    for entry in entries:
        debit_total = sum((line.base_amount for line in entry.lines if line.direction == "debit"), ZERO)
        credit_total = sum((line.base_amount for line in entry.lines if line.direction == "credit"), ZERO)
        if debit_total != credit_total:
            unbalanced_entries.append(f"{entry.id} 借方 {debit_total} 贷方 {credit_total}")

    if unbalanced_entries:
        return AccountingIntegrityCheck(
            check_code="journal_entries_balanced",
            check_name="正式分录借贷平衡",
            status="fail",
            severity="blocking",
            message="存在借贷不平衡的正式分录，不能进入上线验收。",
            affected_count=len(unbalanced_entries),
            evidence=unbalanced_entries,
        )
    return AccountingIntegrityCheck(
        check_code="journal_entries_balanced",
        check_name="正式分录借贷平衡",
        status="pass",
        severity="blocking",
        message="本期正式分录借贷金额全部平衡。",
        affected_count=len(entries),
    )


def _check_duplicate_source_keys(entries: list[JournalEntryRecord]) -> AccountingIntegrityCheck:
    seen: dict[tuple[str, str], str] = {}
    duplicates: list[str] = []
    for entry in entries:
        source_key = (entry.source_type, entry.source_id)
        existing_entry_id = seen.get(source_key)
        if existing_entry_id:
            duplicates.append(f"{entry.source_type}:{entry.source_id} -> {existing_entry_id}, {entry.id}")
            continue
        seen[source_key] = entry.id

    if duplicates:
        return AccountingIntegrityCheck(
            check_code="duplicate_source_keys",
            check_name="来源单据重复过账",
            status="fail",
            severity="blocking",
            message="同一来源单据存在多笔正式分录，需要先完成差异处理。",
            affected_count=len(duplicates),
            evidence=duplicates,
        )
    return AccountingIntegrityCheck(
        check_code="duplicate_source_keys",
        check_name="来源单据重复过账",
        status="pass",
        severity="blocking",
        message="未发现同一来源单据重复正式过账。",
        affected_count=len(entries),
    )


def _check_closed_period_unapproved_entries(
    account_set_id: str,
    period: str,
    entries: list[JournalEntryRecord],
) -> AccountingIntegrityCheck:
    if not is_accounting_period_closed(period=period, account_set_id=account_set_id):
        return AccountingIntegrityCheck(
            check_code="closed_period_unapproved_entries",
            check_name="已关账期间未批准分录",
            status="pass",
            severity="blocking",
            message="本期间尚未关账，无关账后未批准分录风险。",
            affected_count=0,
        )

    unapproved_entries = [entry.id for entry in entries if entry.status != "posted"]
    if unapproved_entries:
        return AccountingIntegrityCheck(
            check_code="closed_period_unapproved_entries",
            check_name="已关账期间未批准分录",
            status="fail",
            severity="blocking",
            message="已关账期间存在非正式过账状态的分录。",
            affected_count=len(unapproved_entries),
            evidence=unapproved_entries,
        )
    return AccountingIntegrityCheck(
        check_code="closed_period_unapproved_entries",
        check_name="已关账期间未批准分录",
        status="pass",
        severity="blocking",
        message="已关账期间分录均为正式过账状态。",
        affected_count=len(entries),
    )


def _check_statement_mapping_coverage(account_set_id: str) -> AccountingIntegrityCheck:
    mapping_set = get_default_statement_mapping_set(account_set_id)
    rules = [rule for rule in list_statement_mapping_rules(mapping_set.mapping_set_id) if rule.enabled]
    if not mapping_set.enabled or not rules:
        return AccountingIntegrityCheck(
            check_code="statement_mapping_coverage",
            check_name="报表映射覆盖",
            status="fail",
            severity="blocking",
            message="默认报表映射集未启用或没有启用规则。",
            affected_count=0,
            evidence=[mapping_set.mapping_set_id],
        )
    statement_types = sorted({rule.statement_type for rule in rules})
    return AccountingIntegrityCheck(
        check_code="statement_mapping_coverage",
        check_name="报表映射覆盖",
        status="pass",
        severity="blocking",
        message="默认报表映射集已启用，覆盖主要财务报表项目。",
        affected_count=len(rules),
        evidence=statement_types,
    )


def _check_attachment_archive_links(
    account_set_id: str,
    period: str,
    entries: list[JournalEntryRecord],
) -> AccountingIntegrityCheck:
    documents = list_archive_documents(account_set_id=account_set_id, period=period).documents
    missing_links = [
        entry.id
        for entry in entries
        if not _has_entry_archive_document(entry, documents)
    ]
    if missing_links:
        return AccountingIntegrityCheck(
            check_code="attachment_archive_links",
            check_name="凭证附件归档链接",
            status="warning",
            severity="warning",
            message="部分正式分录尚未关联会计档案附件，上线前应补齐或保留书面豁免。",
            affected_count=len(missing_links),
            evidence=missing_links,
        )
    return AccountingIntegrityCheck(
        check_code="attachment_archive_links",
        check_name="凭证附件归档链接",
        status="pass",
        severity="warning",
        message="本期正式分录均已关联会计档案附件。",
        affected_count=len(entries),
    )


def _has_entry_archive_document(entry: JournalEntryRecord, documents: list[ArchiveDocument]) -> bool:
    for document in documents:
        if document.source_type == "journal_entry" and document.source_id == entry.id:
            return True
        if document.source_type == "voucher" and document.source_id == entry.source_id:
            return True
    return False


def _overall_status(checks: list[AccountingIntegrityCheck]) -> CheckStatus:
    if any(check.status == "fail" for check in checks):
        return "fail"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
