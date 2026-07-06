import { useMemo, useState } from "react";
import { EXCEL_TEMPLATE_URL, importExcel } from "../services/dashboardApi";
import type { FieldMapping, ImportPreview, MonthlyFinanceRecord } from "../types/dashboard";

interface DataEntryPanelProps {
  records: MonthlyFinanceRecord[];
  defaultPeriod: string;
  onApply: (records: MonthlyFinanceRecord[], period: string) => Promise<void>;
  onRestoreSample: () => Promise<void>;
  onClose: () => void;
}

type FieldKey = keyof MonthlyFinanceRecord;

const editableFields: Array<{ key: FieldKey; label: string; width: number }> = [
  { key: "period", label: "期间", width: 110 },
  { key: "revenue", label: "营业收入", width: 120 },
  { key: "cost", label: "营业成本", width: 120 },
  { key: "sales_expense", label: "销售费用", width: 110 },
  { key: "admin_expense", label: "管理费用", width: 110 },
  { key: "rd_expense", label: "研发费用", width: 110 },
  { key: "finance_expense", label: "财务费用", width: 110 },
  { key: "net_profit", label: "净利润", width: 110 },
  { key: "cash", label: "货币资金", width: 110 },
  { key: "accounts_receivable", label: "应收账款", width: 110 },
  { key: "inventory", label: "存货", width: 100 },
  { key: "fixed_assets", label: "固定资产", width: 110 },
  { key: "total_assets", label: "资产总额", width: 110 },
  { key: "short_term_loans", label: "短期借款", width: 110 },
  { key: "accounts_payable", label: "应付账款", width: 110 },
  { key: "total_liabilities", label: "负债总额", width: 110 },
  { key: "owner_equity", label: "所有者权益", width: 120 },
  { key: "operating_cash_flow_net", label: "经营现金流净额", width: 140 },
  { key: "investing_cash_flow_net", label: "投资现金流净额", width: 140 },
  { key: "financing_cash_flow_net", label: "筹资现金流净额", width: 140 },
  { key: "inventory_turnover_days", label: "库存周转天数", width: 130 },
  { key: "tax_burden_rate", label: "税负率", width: 100 }
];

function createBlankRecord(period: string): MonthlyFinanceRecord {
  return {
    period,
    revenue: 0,
    cost: 0,
    sales_expense: 0,
    admin_expense: 0,
    rd_expense: 0,
    finance_expense: 0,
    total_profit: 0,
    net_profit: 0,
    cash: 0,
    accounts_receivable: 0,
    inventory: 0,
    fixed_assets: 0,
    total_assets: 0,
    short_term_loans: 0,
    accounts_payable: 0,
    total_liabilities: 0,
    owner_equity: 0,
    operating_cash_inflow: 0,
    operating_cash_outflow: 0,
    operating_cash_flow_net: 0,
    investing_cash_flow_net: 0,
    financing_cash_flow_net: 0,
    customer_collection: 0,
    sales_orders: 0,
    purchase_amount: 0,
    inventory_turnover_days: 0,
    tax_burden_rate: 0
  };
}

function nextPeriod(records: MonthlyFinanceRecord[], fallback: string) {
  const last = records.at(-1)?.period ?? fallback;
  const [yearText, monthText] = last.split("-");
  const date = new Date(Number(yearText), Number(monthText), 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function mappingStatusText(mapping: FieldMapping) {
  if (mapping.status === "matched") {
    return "已识别";
  }
  return mapping.required ? "必填缺失" : "可选缺失";
}

function mappingStatusClass(mapping: FieldMapping) {
  if (mapping.status === "matched") {
    return "matched";
  }
  return mapping.required ? "missing-required" : "missing-optional";
}

export default function DataEntryPanel({
  records,
  defaultPeriod,
  onApply,
  onRestoreSample,
  onClose
}: DataEntryPanelProps) {
  const [draftRecords, setDraftRecords] = useState<MonthlyFinanceRecord[]>(records);
  const [period, setPeriod] = useState(defaultPeriod);
  const [message, setMessage] = useState<string>("支持 Excel .xlsx/.xlsm；WPS 表格请先另存为 .xlsx。");
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const periodOptions = useMemo(
    () => draftRecords.map((record) => record.period).filter(Boolean),
    [draftRecords]
  );
  const mappingStats = useMemo(() => {
    const mappings = importPreview?.field_mappings ?? [];
    const requiredMappings = mappings.filter((mapping) => mapping.required);
    return {
      requiredTotal: requiredMappings.length,
      requiredMatched: requiredMappings.filter((mapping) => mapping.matched).length,
      missingRequired: requiredMappings.filter((mapping) => !mapping.matched),
      missingOptional: mappings.filter((mapping) => !mapping.required && !mapping.matched)
    };
  }, [importPreview]);

  function updateCell(rowIndex: number, key: FieldKey, value: string) {
    setDraftRecords((current) =>
      current.map((record, index) => {
        if (index !== rowIndex) {
          return record;
        }

        if (key === "period") {
          return { ...record, period: value };
        }

        const numericValue = Number(value);
        const nextRecord = {
          ...record,
          [key]: Number.isFinite(numericValue) ? numericValue : 0
        };

        nextRecord.total_profit = nextRecord.total_profit || nextRecord.net_profit;
        nextRecord.operating_cash_inflow =
          nextRecord.operating_cash_inflow || Math.max(nextRecord.operating_cash_flow_net, 0);
        nextRecord.operating_cash_outflow =
          nextRecord.operating_cash_outflow || Math.max(-nextRecord.operating_cash_flow_net, 0);
        nextRecord.customer_collection =
          nextRecord.customer_collection || Math.max(nextRecord.operating_cash_flow_net, 0);
        nextRecord.sales_orders = nextRecord.sales_orders || nextRecord.revenue;
        nextRecord.purchase_amount = nextRecord.purchase_amount || nextRecord.cost;
        return nextRecord;
      })
    );
  }

  async function handleFileUpload(file: File | undefined) {
    if (!file) {
      return;
    }

    setIsBusy(true);
    try {
      const preview = await importExcel(file);
      setDraftRecords(preview.records);
      setImportPreview(preview);
      setPeriod(preview.records.at(-1)?.period ?? defaultPeriod);
      setMessage(
        `已识别 ${preview.sheet_name}：${preview.records.length} 期数据；字段：${preview.matched_fields.join("、")}`
      );
    } catch (error) {
      setImportPreview(null);
      setMessage(error instanceof Error ? error.message : "导入失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleApply() {
    if (!draftRecords.some((record) => record.period === period)) {
      setMessage("请选择或填写一个存在于表格中的分析期间。");
      return;
    }

    setIsBusy(true);
    try {
      await onApply(draftRecords, period);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "分析失败");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <section className="data-entry-panel">
        <header className="data-entry-header">
          <div>
            <span className="eyebrow">数据录入中心</span>
            <h2>导入 Excel / WPS 表格或手动填写报表数据</h2>
            <p>{message}</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="关闭">×</button>
        </header>

        <div className="data-entry-toolbar">
          <label className="file-picker">
            <span>上传 Excel / WPS 导出的 .xlsx</span>
            <input
              type="file"
              accept=".xlsx,.xlsm"
              onChange={(event) => handleFileUpload(event.target.files?.[0])}
            />
          </label>

          <a
            className="button-secondary download-link"
            href={EXCEL_TEMPLATE_URL}
            download="finance-analysis-template.xlsx"
          >
            下载标准模板
          </a>

          <label>
            分析期间
            <select value={period} onChange={(event) => setPeriod(event.target.value)}>
              {periodOptions.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>

          <button
            type="button"
            className="button-secondary"
            onClick={() => setDraftRecords((current) => [...current, createBlankRecord(nextPeriod(current, period))])}
          >
            新增月份
          </button>
          <button type="button" className="button-secondary" onClick={onRestoreSample}>恢复示例数据</button>
          <button type="button" onClick={handleApply} disabled={isBusy}>
            {isBusy ? "处理中..." : "开始分析"}
          </button>
        </div>

        {importPreview ? (
          <section className="field-mapping-panel" aria-label="字段识别确认">
            <div className="field-mapping-summary">
              <div>
                <span className="eyebrow">字段识别确认</span>
                <h3>
                  必填字段 {mappingStats.requiredMatched}/{mappingStats.requiredTotal} 已识别
                </h3>
              </div>
              <div className="mapping-badges">
                <span className="mapping-badge matched">已识别 {importPreview.matched_fields.length}</span>
                <span className={mappingStats.missingRequired.length > 0 ? "mapping-badge missing-required" : "mapping-badge matched"}>
                  必填缺失 {mappingStats.missingRequired.length}
                </span>
                <span className="mapping-badge missing-optional">可选缺失 {mappingStats.missingOptional.length}</span>
              </div>
            </div>

            <div className="field-mapping-grid">
              {importPreview.field_mappings.map((mapping) => (
                <div className={`field-mapping-item ${mappingStatusClass(mapping)}`} key={mapping.field}>
                  <div>
                    <strong>{mapping.label}</strong>
                    <span>{mapping.required ? "必填" : "可选"}</span>
                  </div>
                  <p>{mapping.source_header ? `来源表头：${mapping.source_header}` : "未在上传表格中识别到"}</p>
                  <em>{mappingStatusText(mapping)}</em>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                {editableFields.map((field) => (
                  <th key={field.key} style={{ minWidth: field.width }}>{field.label}</th>
                ))}
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {draftRecords.map((record, rowIndex) => (
                <tr key={`${record.period}-${rowIndex}`}>
                  {editableFields.map((field) => (
                    <td key={field.key}>
                      <input
                        value={String(record[field.key] ?? "")}
                        type={field.key === "period" ? "text" : "number"}
                        step={field.key === "tax_burden_rate" ? "0.001" : "1"}
                        onChange={(event) => updateCell(rowIndex, field.key, event.target.value)}
                      />
                    </td>
                  ))}
                  <td>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => setDraftRecords((current) => current.filter((_, index) => index !== rowIndex))}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
