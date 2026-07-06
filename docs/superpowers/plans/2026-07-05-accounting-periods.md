# Accounting Periods MVP Plan

**Goal:** 增加账套与会计期间管理底座，支持查看默认账套期间、关闭期间、重开期间，并让凭证过账拒绝已关闭期间。

**Architecture:** 复用现有 `ledger` 模块，新增期间状态的轻量服务与 API，不引入正式结账引擎。期间状态先用内存表表达 MVP 流程，权限与审计继续沿用 `system_admin_service`。

## Tasks

1. Add backend red tests for period listing, close/reopen, permission denial, and posted voucher blocking.
2. Add ledger models and service functions for account sets and accounting periods.
3. Add `/api/v1/ledger/account-sets`, `/periods`, `/periods/{period}/close`, `/reopen` with audit logs.
4. Make `post_voucher` reject vouchers whose `voucher_date` month is closed.
5. Add frontend API/types and render period status/actions in `LedgerPanel`.
6. Update docs and run backend/frontend verification.
