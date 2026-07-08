import type {
  AuditRequest,
  AuditResponse
} from "../types/audit";
import type {
  BankBalanceReconciliationStatement,
  BankMatchCandidateResponse,
  BankStatementImportRequest,
  BankStatementImportResult
} from "../types/bankReconciliation";
import type {
  AccountListResponse,
  AuxiliaryDimensionCreateRequest,
  AuxiliaryDimensionListResponse,
  AuxiliaryDimensionRecord,
  CurrencyListResponse,
  ExchangeRateCreateRequest,
  ExchangeRateListResponse,
  ExchangeRateRecord,
  JournalEntryListResponse,
  JournalEntryRecord
} from "../types/accounting";
import type {
  ArchiveCase,
  ArchiveCaseCreateRequest,
  ArchiveDocumentListResponse,
  ArchivePackageDownload
} from "../types/accountingArchive";
import type {
  AccountingBackupManifest,
  AccountingGovernanceScopeRequest,
  AccountingIntegrityReport,
  AccountingMigrationApplyRequest,
  AccountingMigrationPreview,
  FormalAccountingGoLiveGate,
  FormalAccountingPermissionMatrix,
  RestoreRehearsalRequest,
  RestoreRehearsalResult
} from "../types/accountingGovernance";
import type {
  AnalyzeResponse,
  DashboardOverview,
  ImportPreview,
  ManagementReport,
  MonthlyFinanceRecord
} from "../types/dashboard";
import type { ECommerceProfitRequest, ECommerceProfitResult } from "../types/ecommerce";
import type { FinanceQuestionResponse } from "../types/financeQa";
import type {
  FinancialStatementBundle,
  FinancialStatementGenerateRequest
} from "../types/financialStatement";
import type { StatementMappingSetResponse } from "../types/statementMapping";
import type {
  StatementExportDownload,
  StatementExportFormat,
  StatementSnapshot,
  StatementSnapshotCreateRequest,
  StatementSnapshotListResponse,
  StatementSnapshotLockRequest
} from "../types/statementArchive";
import type {
  FixedAssetCreateRequest,
  FixedAssetDepreciationRunRequest,
  FixedAssetDepreciationRunResponse,
  FixedAssetDisposeRequest,
  FixedAssetInventoryRequest,
  FixedAssetListResponse,
  FixedAssetRecord,
  FixedAssetSaleRequest
} from "../types/fixedAsset";
import type {
  FixedAssetAccountingEntryBatch,
  FixedAssetCapitalizationRequest,
  FixedAssetDepreciationPostRequest,
  FixedAssetDisposalAccountingResult,
  FixedAssetDisposalPostRequest,
  FixedAssetImpairmentPostRequest,
  FormalAssetAccountingCardListResponse
} from "../types/fixedAssetAccounting";
import type { HomeDashboard } from "../types/homeDashboard";
import type { InvoiceOcrResponse } from "../types/invoiceOcr";
import type {
  InventoryAccountingSummary,
  InventoryCountVarianceRequest,
  InventoryCountVarianceResult,
  InventoryImpairmentRequest,
  InventoryImpairmentResult,
  InventoryPurchaseReceiptRequest,
  InventorySalesIssueRequest,
  InventorySalesIssueResult,
  InventoryMovement
} from "../types/inventoryAccounting";
import type {
  SurtaxAccrualRequest,
  TaxAccountingEntryResponse,
  TaxAmountPostRequest,
  TaxFilingWorksheet,
  TaxPaymentPostRequest,
  VatLedgerLineListResponse
} from "../types/taxAccounting";
import type {
  AccrualAmortizationEntryResponse,
  AccrualAmortizationScheduleListResponse,
  AccountingSchedule,
  AccountingScheduleCreateRequest,
  LoanInterestPostRequest,
  SchedulePostRequest
} from "../types/accrualAmortization";
import type {
  ConsolidatedStatementResponse,
  ConsolidationEliminationListResponse,
  ConsolidationEliminationRebuildRequest,
  ConsolidationGroup,
  ConsolidationGroupCreateRequest,
  ConsolidationGroupListResponse,
  ConsolidationReportingPackage
} from "../types/consolidation";
import type {
  AccountBalanceTableResponse,
  AccountSetListResponse,
  AccountingPeriodItem,
  AccountingPeriodListResponse,
  DetailLedgerResponse,
  GeneralLedgerResponse
} from "../types/ledger";
import type { PayrollCalculateRequest, PayrollCalculationResponse } from "../types/payroll";
import type {
  PayrollAccountingBatchListResponse,
  PayrollAccountingEntryResponse,
  PayrollAccountingPostRequest,
  PayrollLiabilityPaymentPostRequest,
  PayrollPaymentPostRequest
} from "../types/payrollAccounting";
import type {
  PeriodCloseCheckRequest,
  PeriodCloseCheckResponse,
  PeriodCloseGenerateRequest,
  PeriodCloseGenerateResponse,
  PeriodClosePeriodRequest,
  PeriodClosePeriodResponse
} from "../types/periodClose";
import type { PolicySearchResponse } from "../types/policy";
import type { ApplicationUpdateCheckResult, UpdateCenterStatus, UpdateCheckResult } from "../types/updateCenter";
import type {
  CounterpartyAgingResponse,
  CounterpartyBalanceResponse,
  OpenItemType
} from "../types/receivablePayable";
import type {
  VoucherCenterCreateRequest,
  VoucherCenterImportResponse,
  VoucherCenterListResponse,
  VoucherCenterRecord
} from "../types/voucherCenter";
import type { VoucherDraftRequest, VoucherDraftResponse } from "../types/voucherDraft";

const API_BASE = "http://127.0.0.1:8000";
const DEFAULT_LEDGER_ACTOR_ID = "u-finance-manager";
const DEFAULT_FINANCE_ACTOR_ID = "u-finance-manager";
export const EXCEL_TEMPLATE_URL = `${API_BASE}/api/v1/dashboard/template/excel`;

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestLedgerJson<T>(
  path: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_LEDGER_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    headers: { "X-Actor-Id": actorId }
  });
  if (!response.ok) {
    throw new Error(`账簿 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutateLedgerJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_LEDGER_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`账簿 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestFixedAssetJson<T>(
  path: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    headers: { "X-Actor-Id": actorId }
  });
  if (!response.ok) {
    throw new Error(`固定资产 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutateFixedAssetJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`固定资产 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutatePayrollJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`工资管理 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestPayrollJson<T>(
  path: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    headers: { "X-Actor-Id": actorId }
  });
  if (!response.ok) {
    throw new Error(`工资管理 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutateFinancialStatementJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`财务报表 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutatePeriodCloseJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`期间结账 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestGovernanceJson<T>(
  path: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    headers: { "X-Actor-Id": actorId }
  });
  if (!response.ok) {
    throw new Error(`正式核算上线治理 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutateGovernanceJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`正式核算上线治理 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestInventoryAccountingJson<T>(
  path: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    headers: { "X-Actor-Id": actorId }
  });
  if (!response.ok) {
    throw new Error(`存货核算 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutateInventoryAccountingJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`存货核算 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestTaxAccountingJson<T>(
  path: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    headers: { "X-Actor-Id": actorId }
  });
  if (!response.ok) {
    throw new Error(`税务核算 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutateTaxAccountingJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`税务核算 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestAccrualAmortizationJson<T>(
  path: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    headers: { "X-Actor-Id": actorId }
  });
  if (!response.ok) {
    throw new Error(`预提摊销 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutateAccrualAmortizationJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`预提摊销 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestConsolidationJson<T>(
  path: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    headers: { "X-Actor-Id": actorId }
  });
  if (!response.ok) {
    throw new Error(`合并报表 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function mutateConsolidationJson<T>(
  path: string,
  body: unknown,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<T> {
  const response = await fetcher(`${apiBase}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": actorId
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`合并报表 API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

function withAccountSet(path: string, accountSetId = "default") {
  if (accountSetId === "default") {
    return path;
  }
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}account_set_id=${encodeURIComponent(accountSetId)}`;
}

export function fetchOverview(period: string): Promise<DashboardOverview> {
  return requestJson<DashboardOverview>(`/api/v1/dashboard/overview?period=${period}`);
}

export function fetchHomeDashboard(period: string): Promise<HomeDashboard> {
  return requestJson<HomeDashboard>(`/api/v1/home/dashboard?period=${period}`);
}

export function analyzeHomeDashboard(period: string, records: MonthlyFinanceRecord[]): Promise<HomeDashboard> {
  return fetch(`${API_BASE}/api/v1/home/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ period, records })
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`AI 首页分析失败：${response.status}`);
    }
    return response.json() as Promise<HomeDashboard>;
  });
}

export function fetchReport(period: string): Promise<ManagementReport> {
  return requestJson<ManagementReport>(`/api/v1/dashboard/report?period=${period}`);
}

export function fetchSampleData(): Promise<MonthlyFinanceRecord[]> {
  return requestJson<MonthlyFinanceRecord[]>("/api/v1/dashboard/sample-data");
}

export function analyzeRecords(period: string, records: MonthlyFinanceRecord[]): Promise<AnalyzeResponse> {
  return fetch(`${API_BASE}/api/v1/dashboard/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ period, records })
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`分析失败：${response.status}`);
    }
    return response.json() as Promise<AnalyzeResponse>;
  });
}

export function importExcel(file: File): Promise<ImportPreview> {
  const formData = new FormData();
  formData.append("file", file);

  return fetch(`${API_BASE}/api/v1/dashboard/import/excel`, {
    method: "POST",
    body: formData
  }).then(async (response) => {
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? `导入失败：${response.status}`);
    }
    return response.json() as Promise<ImportPreview>;
  });
}

export async function downloadManagementReport(
  report: ManagementReport,
  format: "docx" | "pdf"
) {
  const response = await fetch(`${API_BASE}/api/v1/dashboard/report/export/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report)
  });

  if (!response.ok) {
    throw new Error(`报告导出失败：${response.status}`);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? `china-finance-report.${format}`;
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export function analyzeECommerceProfit(request: ECommerceProfitRequest): Promise<ECommerceProfitResult> {
  return fetch(`${API_BASE}/api/v1/ecommerce/profit/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`电商利润分析失败：${response.status}`);
    }
    return response.json() as Promise<ECommerceProfitResult>;
  });
}

export function askFinanceQuestion(question: string): Promise<FinanceQuestionResponse> {
  return fetch(`${API_BASE}/api/v1/finance-qa/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`AI 财务问答失败：${response.status}`);
    }
    return response.json() as Promise<FinanceQuestionResponse>;
  });
}

export function searchPolicies(
  query: string,
  category: string | null = null,
  limit = 5
): Promise<PolicySearchResponse> {
  return fetch(`${API_BASE}/api/v1/policies/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, category, limit })
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`法规库检索失败：${response.status}`);
    }
    return response.json() as Promise<PolicySearchResponse>;
  });
}

export function fetchUpdateCenterStatus(
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch
): Promise<UpdateCenterStatus> {
  return fetcher(`${apiBase}/api/v1/update-center/status`).then(async (response) => {
    if (!response.ok) {
      throw new Error(`联网更新中心状态读取失败：${response.status}`);
    }
    return response.json() as Promise<UpdateCenterStatus>;
  });
}

export function checkUpdateCenterNow(
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch
): Promise<UpdateCheckResult> {
  return fetcher(`${apiBase}/api/v1/update-center/check`, { method: "POST" }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`联网更新检查失败：${response.status}`);
    }
    return response.json() as Promise<UpdateCheckResult>;
  });
}

export function checkApplicationUpdateNow(
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch
): Promise<ApplicationUpdateCheckResult> {
  return fetcher(`${apiBase}/api/v1/update-center/application/check`, { method: "POST" }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`软件本体更新检查失败：${response.status}`);
    }
    return response.json() as Promise<ApplicationUpdateCheckResult>;
  });
}

export function recognizeInvoiceText(text: string): Promise<InvoiceOcrResponse> {
  return fetch(`${API_BASE}/api/v1/invoice-ocr/recognize-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`发票 OCR 识别失败：${response.status}`);
    }
    return response.json() as Promise<InvoiceOcrResponse>;
  });
}

export function uploadInvoiceFile(file: File): Promise<InvoiceOcrResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return fetch(`${API_BASE}/api/v1/invoice-ocr/upload`, {
    method: "POST",
    body: formData
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`发票文件上传识别失败：${response.status}`);
    }
    return response.json() as Promise<InvoiceOcrResponse>;
  });
}

export function generateVoucherDraft(request: VoucherDraftRequest): Promise<VoucherDraftResponse> {
  return fetch(`${API_BASE}/api/v1/vouchers/draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`凭证草稿生成失败：${response.status}`);
    }
    return response.json() as Promise<VoucherDraftResponse>;
  });
}

export function reviewAuditSubject(request: AuditRequest): Promise<AuditResponse> {
  return fetch(`${API_BASE}/api/v1/audit/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`自动审核失败：${response.status}`);
    }
    return response.json() as Promise<AuditResponse>;
  });
}

export function fetchVoucherCenter(): Promise<VoucherCenterListResponse> {
  return requestJson<VoucherCenterListResponse>("/api/v1/vouchers/center");
}

export function fetchGeneralLedger(
  period: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_LEDGER_ACTOR_ID,
  accountSetId = "default"
): Promise<GeneralLedgerResponse> {
  return requestLedgerJson<GeneralLedgerResponse>(
    withAccountSet(`/api/v1/ledger/general?period=${encodeURIComponent(period)}`, accountSetId),
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchDetailLedger(
  period: string,
  accountCode: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_LEDGER_ACTOR_ID,
  accountSetId = "default",
  dimensionType: string | null = null,
  dimensionCode: string | null = null
): Promise<DetailLedgerResponse> {
  const dimensionQuery =
    dimensionType && dimensionCode
      ? `&dimension_type=${encodeURIComponent(dimensionType)}&dimension_code=${encodeURIComponent(dimensionCode)}`
      : "";
  return requestLedgerJson<DetailLedgerResponse>(
    withAccountSet(
      `/api/v1/ledger/detail?period=${encodeURIComponent(period)}&account_code=${encodeURIComponent(accountCode)}${dimensionQuery}`,
      accountSetId
    ),
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchAccountBalanceTable(
  period: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_LEDGER_ACTOR_ID,
  accountSetId = "default"
): Promise<AccountBalanceTableResponse> {
  return requestLedgerJson<AccountBalanceTableResponse>(
    withAccountSet(`/api/v1/ledger/account-balances?period=${encodeURIComponent(period)}`, accountSetId),
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchCounterpartyBalances(
  accountSetId = "default",
  period: string,
  openItemType: OpenItemType,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<CounterpartyBalanceResponse> {
  return requestLedgerJson<CounterpartyBalanceResponse>(
    `/api/v1/receivable-payable/balances?account_set_id=${encodeURIComponent(accountSetId)}&period=${encodeURIComponent(period)}&open_item_type=${openItemType}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchCounterpartyAging(
  accountSetId = "default",
  period: string,
  openItemType: OpenItemType,
  asOfDate: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<CounterpartyAgingResponse> {
  return requestLedgerJson<CounterpartyAgingResponse>(
    `/api/v1/receivable-payable/aging?account_set_id=${encodeURIComponent(accountSetId)}&period=${encodeURIComponent(period)}&open_item_type=${openItemType}&as_of_date=${encodeURIComponent(asOfDate)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchBankReconciliationStatement(
  accountSetId: string,
  bankAccountId: string,
  period: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<BankBalanceReconciliationStatement> {
  const query = new URLSearchParams({
    account_set_id: accountSetId,
    bank_account_id: bankAccountId,
    period
  });
  return requestLedgerJson<BankBalanceReconciliationStatement>(
    `/api/v1/bank-reconciliation/statements?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchBankMatchCandidates(
  accountSetId: string,
  bankAccountId: string,
  period: string,
  minimumScore = 80,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<BankMatchCandidateResponse> {
  const query = new URLSearchParams({
    account_set_id: accountSetId,
    bank_account_id: bankAccountId,
    period,
    minimum_score: String(minimumScore)
  });
  return requestLedgerJson<BankMatchCandidateResponse>(
    `/api/v1/bank-reconciliation/matches?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function importBankStatementLines(
  request: BankStatementImportRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<BankStatementImportResult> {
  return mutateLedgerJson<BankStatementImportResult>(
    "/api/v1/bank-reconciliation/statements/import",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchAccountingAccounts(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AccountListResponse> {
  return requestLedgerJson<AccountListResponse>(
    `/api/v1/accounting/accounts?account_set_id=${encodeURIComponent(accountSetId)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchJournalEntries(
  accountSetId = "default",
  period: string | null = null,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<JournalEntryListResponse> {
  const periodQuery = period ? `&period=${encodeURIComponent(period)}` : "";
  return requestLedgerJson<JournalEntryListResponse>(
    `/api/v1/accounting/journal-entries?account_set_id=${encodeURIComponent(accountSetId)}${periodQuery}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchCurrencies(
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<CurrencyListResponse> {
  return requestLedgerJson<CurrencyListResponse>("/api/v1/accounting/currencies", apiBase, fetcher, actorId);
}

export function fetchExchangeRates(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ExchangeRateListResponse> {
  return requestLedgerJson<ExchangeRateListResponse>(
    `/api/v1/accounting/exchange-rates?account_set_id=${encodeURIComponent(accountSetId)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function saveExchangeRate(
  request: ExchangeRateCreateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ExchangeRateRecord> {
  return mutateLedgerJson<ExchangeRateRecord>("/api/v1/accounting/exchange-rates", request, apiBase, fetcher, actorId);
}

export function fetchAuxiliaryDimensions(
  accountSetId = "default",
  dimensionType: string | null = null,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AuxiliaryDimensionListResponse> {
  const typeQuery = dimensionType ? `&dimension_type=${encodeURIComponent(dimensionType)}` : "";
  return requestLedgerJson<AuxiliaryDimensionListResponse>(
    `/api/v1/accounting/dimensions?account_set_id=${encodeURIComponent(accountSetId)}${typeQuery}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function saveAuxiliaryDimension(
  request: AuxiliaryDimensionCreateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AuxiliaryDimensionRecord> {
  return mutateLedgerJson<AuxiliaryDimensionRecord>("/api/v1/accounting/dimensions", request, apiBase, fetcher, actorId);
}

export function fetchAccountSets(
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_LEDGER_ACTOR_ID
): Promise<AccountSetListResponse> {
  return requestLedgerJson<AccountSetListResponse>(
    "/api/v1/ledger/account-sets",
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchAccountingPeriods(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_LEDGER_ACTOR_ID
): Promise<AccountingPeriodListResponse> {
  return requestLedgerJson<AccountingPeriodListResponse>(
    `/api/v1/ledger/periods?account_set_id=${encodeURIComponent(accountSetId)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function closeAccountingPeriod(
  period: string,
  operator = "财务主管",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_LEDGER_ACTOR_ID,
  accountSetId = "default"
): Promise<AccountingPeriodItem> {
  return mutateLedgerJson<AccountingPeriodItem>(
    withAccountSet(`/api/v1/ledger/periods/${encodeURIComponent(period)}/close`, accountSetId),
    { operator },
    apiBase,
    fetcher,
    actorId
  );
}

export function reopenAccountingPeriod(
  period: string,
  operator = "财务主管",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_LEDGER_ACTOR_ID,
  accountSetId = "default"
): Promise<AccountingPeriodItem> {
  return mutateLedgerJson<AccountingPeriodItem>(
    withAccountSet(`/api/v1/ledger/periods/${encodeURIComponent(period)}/reopen`, accountSetId),
    { operator },
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchFixedAssets(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FixedAssetListResponse> {
  return requestFixedAssetJson<FixedAssetListResponse>(
    `/api/v1/fixed-assets?account_set_id=${encodeURIComponent(accountSetId)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function createFixedAsset(
  request: FixedAssetCreateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FixedAssetRecord> {
  return mutateFixedAssetJson<FixedAssetRecord>(
    "/api/v1/fixed-assets",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function runMonthlyDepreciation(
  request: FixedAssetDepreciationRunRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FixedAssetDepreciationRunResponse> {
  return mutateFixedAssetJson<FixedAssetDepreciationRunResponse>(
    "/api/v1/fixed-assets/depreciation/run",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function inventoryFixedAsset(
  assetId: string,
  request: FixedAssetInventoryRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FixedAssetRecord> {
  return mutateFixedAssetJson<FixedAssetRecord>(
    `/api/v1/fixed-assets/${encodeURIComponent(assetId)}/inventory`,
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function disposeFixedAsset(
  assetId: string,
  request: FixedAssetDisposeRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FixedAssetRecord> {
  return mutateFixedAssetJson<FixedAssetRecord>(
    `/api/v1/fixed-assets/${encodeURIComponent(assetId)}/dispose`,
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function sellFixedAsset(
  assetId: string,
  request: FixedAssetSaleRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FixedAssetRecord> {
  return mutateFixedAssetJson<FixedAssetRecord>(
    `/api/v1/fixed-assets/${encodeURIComponent(assetId)}/sell`,
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchFixedAssetAccountingCards(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FormalAssetAccountingCardListResponse> {
  return requestFixedAssetJson<FormalAssetAccountingCardListResponse>(
    `/api/v1/fixed-asset-accounting/cards?account_set_id=${encodeURIComponent(accountSetId)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function capitalizeFixedAsset(
  request: FixedAssetCapitalizationRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<JournalEntryRecord> {
  return mutateFixedAssetJson<JournalEntryRecord>(
    "/api/v1/fixed-asset-accounting/capitalize",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function postFixedAssetDepreciation(
  request: FixedAssetDepreciationPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FixedAssetAccountingEntryBatch> {
  return mutateFixedAssetJson<FixedAssetAccountingEntryBatch>(
    "/api/v1/fixed-asset-accounting/depreciation",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function recordFixedAssetImpairment(
  request: FixedAssetImpairmentPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<JournalEntryRecord> {
  return mutateFixedAssetJson<JournalEntryRecord>(
    "/api/v1/fixed-asset-accounting/impairment",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function disposeFixedAssetFormally(
  request: FixedAssetDisposalPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FixedAssetDisposalAccountingResult> {
  return mutateFixedAssetJson<FixedAssetDisposalAccountingResult>(
    "/api/v1/fixed-asset-accounting/disposal",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchInventoryAccountingBalances(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<InventoryAccountingSummary> {
  return requestInventoryAccountingJson<InventoryAccountingSummary>(
    `/api/v1/inventory-accounting/balances?account_set_id=${encodeURIComponent(accountSetId)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function postInventoryPurchaseReceipt(
  request: InventoryPurchaseReceiptRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<InventoryMovement> {
  return mutateInventoryAccountingJson<InventoryMovement>(
    "/api/v1/inventory-accounting/purchase-receipts",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function postInventorySalesIssue(
  request: InventorySalesIssueRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<InventorySalesIssueResult> {
  return mutateInventoryAccountingJson<InventorySalesIssueResult>(
    "/api/v1/inventory-accounting/sales-issues",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function recordInventoryImpairment(
  request: InventoryImpairmentRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<InventoryImpairmentResult> {
  return mutateInventoryAccountingJson<InventoryImpairmentResult>(
    "/api/v1/inventory-accounting/impairments",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function recordInventoryCountVariance(
  request: InventoryCountVarianceRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<InventoryCountVarianceResult> {
  return mutateInventoryAccountingJson<InventoryCountVarianceResult>(
    "/api/v1/inventory-accounting/count-variances",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchVatLedger(
  accountSetId: string,
  period: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<VatLedgerLineListResponse> {
  const query = new URLSearchParams({ account_set_id: accountSetId, period });
  return requestTaxAccountingJson<VatLedgerLineListResponse>(
    `/api/v1/tax-accounting/vat-ledger?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchTaxFilingWorksheet(
  accountSetId: string,
  period: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<TaxFilingWorksheet> {
  const query = new URLSearchParams({ account_set_id: accountSetId, period });
  return requestTaxAccountingJson<TaxFilingWorksheet>(
    `/api/v1/tax-accounting/filing-worksheet?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function postUnpaidVatTransfer(
  request: TaxAmountPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<TaxAccountingEntryResponse> {
  return mutateTaxAccountingJson<TaxAccountingEntryResponse>(
    "/api/v1/tax-accounting/unpaid-vat-transfer",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function postSurtaxAccrual(
  request: SurtaxAccrualRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<TaxAccountingEntryResponse> {
  return mutateTaxAccountingJson<TaxAccountingEntryResponse>(
    "/api/v1/tax-accounting/surtax-accrual",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function postIncomeTaxAccrual(
  request: TaxAmountPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<TaxAccountingEntryResponse> {
  return mutateTaxAccountingJson<TaxAccountingEntryResponse>(
    "/api/v1/tax-accounting/income-tax-accrual",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function postTaxPayment(
  request: TaxPaymentPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<TaxAccountingEntryResponse> {
  return mutateTaxAccountingJson<TaxAccountingEntryResponse>(
    "/api/v1/tax-accounting/tax-payments",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchAccrualAmortizationSchedules(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AccrualAmortizationScheduleListResponse> {
  return requestAccrualAmortizationJson<AccrualAmortizationScheduleListResponse>(
    `/api/v1/accrual-amortization/schedules?account_set_id=${encodeURIComponent(accountSetId)}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function createAccountingSchedule(
  request: AccountingScheduleCreateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AccountingSchedule> {
  return mutateAccrualAmortizationJson<AccountingSchedule>(
    "/api/v1/accrual-amortization/schedules",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function postAccountingScheduleForPeriod(
  scheduleCode: string,
  request: SchedulePostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AccrualAmortizationEntryResponse> {
  return mutateAccrualAmortizationJson<AccrualAmortizationEntryResponse>(
    `/api/v1/accrual-amortization/schedules/${encodeURIComponent(scheduleCode)}/post`,
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function postLoanInterestAccrual(
  request: LoanInterestPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AccrualAmortizationEntryResponse> {
  return mutateAccrualAmortizationJson<AccrualAmortizationEntryResponse>(
    "/api/v1/accrual-amortization/loan-interest",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchConsolidationGroups(
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ConsolidationGroupListResponse> {
  return requestConsolidationJson<ConsolidationGroupListResponse>(
    "/api/v1/consolidation/groups",
    apiBase,
    fetcher,
    actorId
  );
}

export function createConsolidationGroup(
  request: ConsolidationGroupCreateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ConsolidationGroup> {
  return mutateConsolidationJson<ConsolidationGroup>(
    "/api/v1/consolidation/groups",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchConsolidationReportingPackage(
  accountSetId: string,
  period: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ConsolidationReportingPackage> {
  const query = new URLSearchParams({ account_set_id: accountSetId, period });
  return requestConsolidationJson<ConsolidationReportingPackage>(
    `/api/v1/consolidation/reporting-package?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchConsolidationEliminations(
  groupId: string,
  period: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ConsolidationEliminationListResponse> {
  const query = new URLSearchParams({ group_id: groupId, period });
  return requestConsolidationJson<ConsolidationEliminationListResponse>(
    `/api/v1/consolidation/eliminations?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function rebuildConsolidationEliminations(
  request: ConsolidationEliminationRebuildRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ConsolidationEliminationListResponse> {
  return mutateConsolidationJson<ConsolidationEliminationListResponse>(
    "/api/v1/consolidation/eliminations/rebuild",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchConsolidatedStatements(
  groupId: string,
  period: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ConsolidatedStatementResponse> {
  const query = new URLSearchParams({ group_id: groupId, period });
  return requestConsolidationJson<ConsolidatedStatementResponse>(
    `/api/v1/consolidation/statements?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function calculatePayroll(
  request: PayrollCalculateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<PayrollCalculationResponse> {
  return mutatePayrollJson<PayrollCalculationResponse>(
    "/api/v1/payroll/calculate",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchPayrollAccountingBatches(
  accountSetId: string,
  period: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<PayrollAccountingBatchListResponse> {
  const query = new URLSearchParams({ account_set_id: accountSetId, period });
  return requestPayrollJson<PayrollAccountingBatchListResponse>(
    `/api/v1/payroll-accounting/batches?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function accruePayrollBatch(
  request: PayrollAccountingPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<PayrollAccountingEntryResponse> {
  return mutatePayrollJson<PayrollAccountingEntryResponse>(
    "/api/v1/payroll-accounting/accruals",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function payPayrollBatch(
  request: PayrollPaymentPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<PayrollAccountingEntryResponse> {
  return mutatePayrollJson<PayrollAccountingEntryResponse>(
    "/api/v1/payroll-accounting/payments",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function remitPayrollLiabilities(
  request: PayrollLiabilityPaymentPostRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<PayrollAccountingEntryResponse> {
  return mutatePayrollJson<PayrollAccountingEntryResponse>(
    "/api/v1/payroll-accounting/liability-payments",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function generateFinancialStatements(
  request: FinancialStatementGenerateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FinancialStatementBundle> {
  return mutateFinancialStatementJson<FinancialStatementBundle>(
    "/api/v1/financial-statements/generate",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchDefaultStatementMappingSet(
  accountSetId = "default",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<StatementMappingSetResponse> {
  return fetcher(
    `${apiBase}/api/v1/financial-statements/mapping-sets/default?account_set_id=${encodeURIComponent(accountSetId)}`,
    { headers: { "X-Actor-Id": actorId } }
  ).then(async (response) => {
    if (!response.ok) {
      throw new Error(`报表映射 API 请求失败：${response.status}`);
    }
    return response.json() as Promise<StatementMappingSetResponse>;
  });
}

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
  period: string | null = null,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<StatementSnapshotListResponse> {
  const query = new URLSearchParams({ account_set_id: accountSetId });
  if (period) {
    query.set("period", period);
  }
  return fetcher(`${apiBase}/api/v1/financial-statements/snapshots?${query.toString()}`, {
    headers: { "X-Actor-Id": actorId }
  }).then(async (response) => {
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

export async function exportStatementSnapshot(
  snapshotId: string,
  exportFormat: StatementExportFormat,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<StatementExportDownload> {
  const response = await fetcher(
    `${apiBase}/api/v1/financial-statements/snapshots/${encodeURIComponent(snapshotId)}/export/${exportFormat}`,
    { headers: { "X-Actor-Id": actorId } }
  );
  if (!response.ok) {
    throw new Error(`报表导出失败：${response.status}`);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? `financial-statements.${exportFormat}`;

  if (typeof window !== "undefined" && typeof document !== "undefined") {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }

  return { blob, filename };
}

export function fetchAccountingArchiveDocuments(
  accountSetId = "default",
  period = "",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ArchiveDocumentListResponse> {
  const query = new URLSearchParams({ account_set_id: accountSetId });
  if (period) {
    query.set("period", period);
  }
  return fetcher(`${apiBase}/api/v1/accounting-archive/documents?${query.toString()}`, {
    headers: { "X-Actor-Id": actorId }
  }).then(async (response) => {
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

export async function downloadAccountingArchivePackage(
  archiveCaseId: string,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<ArchivePackageDownload> {
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

  if (typeof window !== "undefined" && typeof document !== "undefined") {
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }

  return { blob, filename };
}

export function fetchAccountingIntegrityChecks(
  accountSetId = "default",
  period = "2026-06",
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AccountingIntegrityReport> {
  const query = new URLSearchParams({ account_set_id: accountSetId, period });
  return requestGovernanceJson<AccountingIntegrityReport>(
    `/api/v1/accounting-governance/integrity-checks?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function previewAccountingMigration(
  request: AccountingGovernanceScopeRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AccountingMigrationPreview> {
  return mutateGovernanceJson<AccountingMigrationPreview>(
    "/api/v1/accounting-governance/migration-preview",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function applyAccountingMigration(
  request: AccountingMigrationApplyRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<unknown> {
  return mutateGovernanceJson<unknown>(
    "/api/v1/accounting-governance/migration-apply",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function createAccountingBackup(
  request: AccountingGovernanceScopeRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<AccountingBackupManifest> {
  return mutateGovernanceJson<AccountingBackupManifest>(
    "/api/v1/accounting-governance/backups",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function rehearseAccountingRestore(
  request: RestoreRehearsalRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<RestoreRehearsalResult> {
  return mutateGovernanceJson<RestoreRehearsalResult>(
    "/api/v1/accounting-governance/restore-rehearsals",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchAccountingPermissionMatrix(
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FormalAccountingPermissionMatrix> {
  return requestGovernanceJson<FormalAccountingPermissionMatrix>(
    "/api/v1/accounting-governance/permission-matrix",
    apiBase,
    fetcher,
    actorId
  );
}

export function fetchAccountingGoLiveGate(
  accountSetId = "default",
  period = "2026-06",
  regressionResults: Record<string, string> = {},
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<FormalAccountingGoLiveGate> {
  const query = new URLSearchParams({ account_set_id: accountSetId, period });
  for (const [key, value] of Object.entries(regressionResults)) {
    query.set(key, value);
  }
  return requestGovernanceJson<FormalAccountingGoLiveGate>(
    `/api/v1/accounting-governance/go-live-gate?${query.toString()}`,
    apiBase,
    fetcher,
    actorId
  );
}

export function runPeriodCloseChecks(
  request: PeriodCloseCheckRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<PeriodCloseCheckResponse> {
  return mutatePeriodCloseJson<PeriodCloseCheckResponse>(
    "/api/v1/period-close/checks",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function generatePeriodCloseActions(
  request: PeriodCloseGenerateRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<PeriodCloseGenerateResponse> {
  return mutatePeriodCloseJson<PeriodCloseGenerateResponse>(
    "/api/v1/period-close/actions/generate",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function closePeriod(
  request: PeriodClosePeriodRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<PeriodClosePeriodResponse> {
  return mutatePeriodCloseJson<PeriodClosePeriodResponse>(
    "/api/v1/period-close/close",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function reopenPeriod(
  request: PeriodClosePeriodRequest,
  apiBase = API_BASE,
  fetcher: typeof fetch = fetch,
  actorId = DEFAULT_FINANCE_ACTOR_ID
): Promise<PeriodClosePeriodResponse> {
  return mutatePeriodCloseJson<PeriodClosePeriodResponse>(
    "/api/v1/period-close/reopen",
    request,
    apiBase,
    fetcher,
    actorId
  );
}

export function createVoucherCenterRecord(request: VoucherCenterCreateRequest): Promise<VoucherCenterRecord> {
  return fetch(`${API_BASE}/api/v1/vouchers/center`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`新增凭证失败：${response.status}`);
    }
    return response.json() as Promise<VoucherCenterRecord>;
  });
}

export function updateVoucherCenterRecord(id: string, request: VoucherCenterCreateRequest): Promise<VoucherCenterRecord> {
  return fetch(`${API_BASE}/api/v1/vouchers/center/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request)
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`修改凭证失败：${response.status}`);
    }
    return response.json() as Promise<VoucherCenterRecord>;
  });
}

export function reviewVoucherCenterRecord(id: string, reviewer: string): Promise<VoucherCenterRecord> {
  return fetch(`${API_BASE}/api/v1/vouchers/center/${id}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer })
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`审核凭证失败：${response.status}`);
    }
    return response.json() as Promise<VoucherCenterRecord>;
  });
}

export function unreviewVoucherCenterRecord(id: string): Promise<VoucherCenterRecord> {
  return fetch(`${API_BASE}/api/v1/vouchers/center/${id}/unreview`, {
    method: "POST"
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`反审核凭证失败：${response.status}`);
    }
    return response.json() as Promise<VoucherCenterRecord>;
  });
}

export function postVoucherCenterRecord(id: string, operator = "财务主管"): Promise<VoucherCenterRecord> {
  return fetch(`${API_BASE}/api/v1/vouchers/center/${id}/post`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": DEFAULT_FINANCE_ACTOR_ID
    },
    body: JSON.stringify({ operator })
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`凭证过账失败：${response.status}`);
    }
    return response.json() as Promise<VoucherCenterRecord>;
  });
}

export function unpostVoucherCenterRecord(id: string, operator = "财务主管"): Promise<VoucherCenterRecord> {
  return fetch(`${API_BASE}/api/v1/vouchers/center/${id}/unpost`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Actor-Id": DEFAULT_FINANCE_ACTOR_ID
    },
    body: JSON.stringify({ operator })
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`凭证反过账失败：${response.status}`);
    }
    return response.json() as Promise<VoucherCenterRecord>;
  });
}

export function importVoucherCenterRecords(vouchers: VoucherCenterCreateRequest[]): Promise<VoucherCenterImportResponse> {
  return fetch(`${API_BASE}/api/v1/vouchers/center/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ vouchers })
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`导入凭证失败：${response.status}`);
    }
    return response.json() as Promise<VoucherCenterImportResponse>;
  });
}

export async function downloadVoucherCenterCsv() {
  const response = await fetch(`${API_BASE}/api/v1/vouchers/center/export/csv`);
  if (!response.ok) {
    throw new Error(`导出凭证失败：${response.status}`);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "voucher-center.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export function uploadVoucherCenterAttachment(id: string, file: File): Promise<VoucherCenterRecord> {
  const formData = new FormData();
  formData.append("file", file);
  return fetch(`${API_BASE}/api/v1/vouchers/center/${id}/attachments`, {
    method: "POST",
    body: formData
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`上传附件失败：${response.status}`);
    }
    return response.json() as Promise<VoucherCenterRecord>;
  });
}
