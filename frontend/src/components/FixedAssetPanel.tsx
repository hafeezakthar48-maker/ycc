import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  capitalizeFixedAsset,
  createFixedAsset,
  disposeFixedAsset,
  fetchAccountSets,
  fetchFixedAssetAccountingCards,
  fetchFixedAssets,
  inventoryFixedAsset,
  postFixedAssetDepreciation,
  recordFixedAssetImpairment,
  runMonthlyDepreciation,
  sellFixedAsset,
  disposeFixedAssetFormally
} from "../services/dashboardApi";
import type {
  FixedAssetCreateRequest,
  FixedAssetInventoryRequest,
  FixedAssetRecord,
  FixedAssetSummary,
  MoneyValue
} from "../types/fixedAsset";
import type { FormalAssetAccountingCard } from "../types/fixedAssetAccounting";
import type { AccountSetItem } from "../types/ledger";

interface FixedAssetPanelProps {
  period: string;
}

const emptySummary: FixedAssetSummary = {
  asset_count: 0,
  active_count: 0,
  disposed_count: 0,
  sold_count: 0,
  original_cost_total: 0,
  accumulated_depreciation_total: 0,
  net_book_value_total: 0,
  monthly_depreciation_total: 0
};

const defaultAsset: FixedAssetCreateRequest = {
  account_set_id: "default",
  name: "自动贴标机",
  category: "生产设备",
  acquisition_date: "2026-01-15",
  original_cost: 120000,
  salvage_value: 12000,
  useful_life_months: 60,
  location: "一号仓",
  custodian: "设备管理员"
};

const defaultInventory: FixedAssetInventoryRequest = {
  inventory_date: "2026-06-30",
  location: "一号仓",
  custodian: "设备管理员",
  condition: "正常",
  operator: "盘点员",
  note: "已贴标签"
};

function money(value: MoneyValue | null | undefined) {
  return Number(value ?? 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function statusLabel(asset: FixedAssetRecord) {
  if (asset.status === "sold") {
    return "已出售";
  }
  if (asset.status === "disposed") {
    return "已报废";
  }
  return "在用";
}

function inventoryLabel(asset: FixedAssetRecord) {
  return asset.inventory_status === "checked" ? "已盘点" : "未盘点";
}

function formalStatusLabel(card: FormalAssetAccountingCard | null | undefined) {
  if (!card) {
    return "未入账";
  }
  const labels: Record<string, string> = {
    not_capitalized: "未入账",
    capitalized: "已入账",
    depreciating: "折旧中",
    impaired: "已减值",
    disposed: "已处置",
    sold: "已出售"
  };
  return labels[card.formal_accounting_status] ?? card.formal_accounting_status;
}

function periodEndDate(period: string) {
  const [year, month] = period.split("-").map(Number);
  const date = new Date(year, month, 0);
  return `${year}-${String(month).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export default function FixedAssetPanel({ period }: FixedAssetPanelProps) {
  const [assets, setAssets] = useState<FixedAssetRecord[]>([]);
  const [formalCards, setFormalCards] = useState<FormalAssetAccountingCard[]>([]);
  const [summary, setSummary] = useState<FixedAssetSummary>(emptySummary);
  const [accountSets, setAccountSets] = useState<AccountSetItem[]>([]);
  const [selectedAccountSetId, setSelectedAccountSetId] = useState("default");
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [form, setForm] = useState<FixedAssetCreateRequest>(defaultAsset);
  const [inventoryForm, setInventoryForm] = useState<FixedAssetInventoryRequest>(defaultInventory);
  const [lastDepreciationMessage, setLastDepreciationMessage] = useState<string | null>(null);
  const [lastFormalAccountingMessage, setLastFormalAccountingMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const selectedAsset = useMemo(
    () => assets.find((asset) => asset.id === selectedAssetId) ?? assets[0] ?? null,
    [assets, selectedAssetId]
  );
  const formalCardByAssetId = useMemo(
    () => new Map(formalCards.map((card) => [card.asset_id, card])),
    [formalCards]
  );
  const selectedFormalCard = selectedAsset ? formalCardByAssetId.get(selectedAsset.id) ?? null : null;
  const selectedAccountSet = accountSets.find((accountSet) => accountSet.id === selectedAccountSetId) ?? accountSets[0] ?? null;

  async function reload(nextSelectedId = selectedAssetId) {
    const [assetPayload, formalPayload, accountSetPayload] = await Promise.all([
      fetchFixedAssets(selectedAccountSetId),
      fetchFixedAssetAccountingCards(selectedAccountSetId).catch(() => ({ account_set_id: selectedAccountSetId, cards: [] })),
      fetchAccountSets().catch(() => ({ account_sets: [] as AccountSetItem[] }))
    ]);
    setAssets(assetPayload.assets);
    setFormalCards(formalPayload.cards);
    setSummary(assetPayload.summary);
    setAccountSets(accountSetPayload.account_sets);
    if (nextSelectedId && assetPayload.assets.some((asset) => asset.id === nextSelectedId)) {
      setSelectedAssetId(nextSelectedId);
    } else {
      setSelectedAssetId(assetPayload.assets[0]?.id ?? null);
    }
  }

  useEffect(() => {
    setForm((current) => ({ ...current, account_set_id: selectedAccountSetId }));
    setError(null);
    reload();
  }, [selectedAccountSetId]);

  useEffect(() => {
    const fallbackAccountSetId = accountSets.find((accountSet) => accountSet.is_default)?.id ?? accountSets[0]?.id;
    if (fallbackAccountSetId && !accountSets.some((accountSet) => accountSet.id === selectedAccountSetId)) {
      setSelectedAccountSetId(fallbackAccountSetId);
    }
  }, [accountSets, selectedAccountSetId]);

  useEffect(() => {
    if (!selectedAsset) {
      return;
    }
    setInventoryForm((current) => ({
      ...current,
      location: selectedAsset.location,
      custodian: selectedAsset.custodian,
      condition: selectedAsset.condition
    }));
  }, [selectedAsset]);

  function updateAssetField(key: keyof FixedAssetCreateRequest, value: string) {
    setForm((current) => {
      if (key === "original_cost" || key === "salvage_value" || key === "useful_life_months") {
        const numericValue = Number(value);
        return { ...current, [key]: Number.isFinite(numericValue) ? numericValue : 0 };
      }
      return { ...current, [key]: value };
    });
  }

  function updateInventoryField(key: keyof FixedAssetInventoryRequest, value: string) {
    setInventoryForm((current) => ({ ...current, [key]: value }));
  }

  async function runAction(action: () => Promise<FixedAssetRecord | void>, nextSelectedId = selectedAssetId) {
    setIsBusy(true);
    setError(null);
    try {
      const result = await action();
      await reload(result && "id" in result ? result.id : nextSelectedId);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "固定资产操作失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function runFormalAction(action: () => Promise<unknown>, successMessage: string, nextSelectedId = selectedAssetId) {
    setIsBusy(true);
    setError(null);
    try {
      await action();
      setLastFormalAccountingMessage(successMessage);
      await reload(nextSelectedId);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "固定资产正式核算失败");
    } finally {
      setIsBusy(false);
    }
  }

  function handleCreate(event: FormEvent) {
    event.preventDefault();
    runAction(() => createFixedAsset({ ...form, account_set_id: selectedAccountSetId }));
  }

  function handleDepreciation() {
    setIsBusy(true);
    setError(null);
    runMonthlyDepreciation({ account_set_id: selectedAccountSetId, period, operator: "财务主管" })
      .then(async (result) => {
        setLastDepreciationMessage(`${period} 计提 ${result.depreciated_count} 项，合计 ${money(result.total_depreciation)}`);
        await reload(selectedAssetId);
      })
      .catch((actionError) => {
        setError(actionError instanceof Error ? actionError.message : "折旧计提失败");
      })
      .finally(() => {
        setIsBusy(false);
      });
  }

  function handleFormalCapitalization() {
    if (!selectedAsset) {
      setError("请先选择要正式入账的固定资产。");
      return;
    }
    runFormalAction(
      () => capitalizeFixedAsset({
        account_set_id: selectedAccountSetId,
        asset_id: selectedAsset.id,
        period: selectedAsset.acquisition_date.slice(0, 7),
        credit_account_code: "2202"
      }),
      `${selectedAsset.asset_code} 已生成资本化分录`,
      selectedAsset.id
    );
  }

  function handleFormalDepreciation() {
    runFormalAction(
      () => postFixedAssetDepreciation({ account_set_id: selectedAccountSetId, period }),
      `${period} 已生成正式折旧分录`,
      selectedAssetId
    );
  }

  function handleImpairment() {
    if (!selectedAsset) {
      setError("请先选择要计提减值的固定资产。");
      return;
    }
    const impairmentAmount = Math.min(Number(selectedAsset.net_book_value), Number(selectedAsset.monthly_depreciation));
    if (impairmentAmount <= 0) {
      setError("当前资产没有可计提的减值金额。");
      return;
    }
    runFormalAction(
      () => recordFixedAssetImpairment({
        account_set_id: selectedAccountSetId,
        asset_id: selectedAsset.id,
        period,
        amount: impairmentAmount
      }),
      `${selectedAsset.asset_code} 已生成减值分录`,
      selectedAsset.id
    );
  }

  function handleFormalDisposal() {
    if (!selectedAsset) {
      setError("请先选择要正式处置的固定资产。");
      return;
    }
    runFormalAction(
      () => disposeFixedAssetFormally({
        account_set_id: selectedAccountSetId,
        asset_id: selectedAsset.id,
        period,
        proceeds_amount: selectedAsset.net_book_value,
        disposal_date: periodEndDate(period)
      }),
      `${selectedAsset.asset_code} 已生成正式处置分录`,
      selectedAsset.id
    );
  }

  function handleInventory() {
    if (!selectedAsset) {
      setError("请先选择要盘点的固定资产。");
      return;
    }
    runAction(() => inventoryFixedAsset(selectedAsset.id, inventoryForm), selectedAsset.id);
  }

  function handleDispose() {
    if (!selectedAsset) {
      setError("请先选择要报废的固定资产。");
      return;
    }
    runAction(
      () => disposeFixedAsset(selectedAsset.id, { disposal_date: periodEndDate(period), reason: "损坏报废", operator: "财务主管" }),
      selectedAsset.id
    );
  }

  function handleSell() {
    if (!selectedAsset) {
      setError("请先选择要出售的固定资产。");
      return;
    }
    runAction(
      () => sellFixedAsset(selectedAsset.id, {
        sale_date: periodEndDate(period),
        sale_amount: selectedAsset.net_book_value,
        reason: "更新换代",
        operator: "财务主管"
      }),
      selectedAsset.id
    );
  }

  return (
    <section id="fixed-asset-panel" className="fixed-asset-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">固定资产</span>
          <h2>台账、折旧、处置与盘点</h2>
        </div>
        <div className="qa-status-strip">
          <span>{selectedAccountSet?.name ?? "默认账套"}</span>
          <span>{summary.active_count} 项在用</span>
          <span>{lastDepreciationMessage ?? `${period} 折旧`}</span>
          <span>{lastFormalAccountingMessage ?? "正式核算"}</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="fixed-asset-toolbar">
        <label>
          <span>账套</span>
          <select
            value={selectedAccountSetId}
            onChange={(event) => setSelectedAccountSetId(event.target.value)}
            aria-label="固定资产账套"
          >
            {(accountSets.length ? accountSets : [{ id: selectedAccountSetId, name: "默认账套" } as AccountSetItem]).map((accountSet) => (
              <option value={accountSet.id} key={accountSet.id}>{accountSet.name}</option>
            ))}
          </select>
        </label>
        <button type="button" onClick={handleDepreciation} disabled={isBusy}>
          计提本月折旧
        </button>
        <button type="button" className="button-secondary" onClick={handleFormalDepreciation} disabled={isBusy}>
          正式折旧
        </button>
      </div>

      <div className="fixed-asset-summary-grid">
        <article>
          <span>资产原值</span>
          <strong>{money(summary.original_cost_total)}</strong>
        </article>
        <article>
          <span>累计折旧</span>
          <strong>{money(summary.accumulated_depreciation_total)}</strong>
        </article>
        <article>
          <span>账面净值</span>
          <strong>{money(summary.net_book_value_total)}</strong>
        </article>
        <article>
          <span>月折旧额</span>
          <strong>{money(summary.monthly_depreciation_total)}</strong>
        </article>
      </div>

      <div className="fixed-asset-grid">
        <section className="panel fixed-asset-table-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">资产台账</span>
              <h3>{summary.asset_count} 项固定资产</h3>
            </div>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table fixed-asset-table">
              <thead>
                <tr>
                  <th>资产</th>
                  <th>类别</th>
                  <th>状态</th>
                  <th>正式</th>
                  <th>原值</th>
                  <th>累计折旧</th>
                  <th>净值</th>
                  <th>位置</th>
                </tr>
              </thead>
              <tbody>
                {assets.length ? assets.map((asset) => (
                  <tr key={asset.id}>
                    <td>
                      <button
                        type="button"
                        className={`ledger-account-button ${selectedAsset?.id === asset.id ? "ledger-account-button--active" : ""}`}
                        onClick={() => setSelectedAssetId(asset.id)}
                      >
                        <strong>{asset.asset_code}</strong>
                        <span>{asset.name}</span>
                      </button>
                    </td>
                    <td>{asset.category}</td>
                    <td><span className={`fixed-asset-status fixed-asset-status--${asset.status}`}>{statusLabel(asset)}</span></td>
                    <td>{formalStatusLabel(formalCardByAssetId.get(asset.id))}</td>
                    <td>{money(asset.original_cost)}</td>
                    <td>{money(asset.accumulated_depreciation)}</td>
                    <td>{money(asset.net_book_value)}</td>
                    <td>{asset.location}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={8}>暂无固定资产</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel fixed-asset-detail-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">生命周期</span>
              <h3>{selectedAsset?.name ?? "未选择资产"}</h3>
            </div>
          </div>
          {selectedAsset ? (
            <div className="fixed-asset-detail">
              <p><span>资产编号</span><strong>{selectedAsset.asset_code}</strong></p>
              <p><span>使用年限</span><strong>{selectedAsset.useful_life_months} 个月</strong></p>
              <p><span>月折旧额</span><strong>{money(selectedAsset.monthly_depreciation)}</strong></p>
              <p><span>上次折旧</span><strong>{selectedAsset.last_depreciated_period ?? "未计提"}</strong></p>
              <p><span>正式入账</span><strong>{formalStatusLabel(selectedFormalCard)}</strong></p>
              <p><span>减值准备</span><strong>{money(selectedFormalCard?.impairment_amount)}</strong></p>
              <p><span>正式净值</span><strong>{money(selectedFormalCard?.net_book_value ?? selectedAsset.net_book_value)}</strong></p>
              <p><span>盘点状态</span><strong>{inventoryLabel(selectedAsset)}</strong></p>
              <div className="fixed-asset-action-row">
                <button type="button" className="button-secondary" onClick={handleFormalCapitalization} disabled={isBusy || selectedAsset.status !== "active"}>
                  资本化
                </button>
                <button type="button" className="button-secondary" onClick={handleImpairment} disabled={isBusy || selectedAsset.status !== "active"}>
                  减值
                </button>
                <button type="button" className="button-secondary" onClick={handleFormalDisposal} disabled={isBusy || selectedAsset.status !== "active"}>
                  正式处置
                </button>
                <button type="button" className="button-secondary" onClick={handleInventory} disabled={isBusy}>
                  盘点
                </button>
                <button type="button" className="button-secondary" onClick={handleDispose} disabled={isBusy || selectedAsset.status !== "active"}>
                  报废
                </button>
                <button type="button" className="button-secondary" onClick={handleSell} disabled={isBusy || selectedAsset.status !== "active"}>
                  出售
                </button>
              </div>
            </div>
          ) : (
            <p className="muted-text">新增资产后可执行盘点、报废和出售。</p>
          )}
        </section>
      </div>

      <section className="panel fixed-asset-accounting-panel">
        <div className="panel-header">
          <div>
            <span className="eyebrow">正式核算</span>
            <h3>固定资产入账、折旧、减值与处置</h3>
          </div>
          <strong>{formalCards.length}</strong>
        </div>
        <div className="voucher-table-wrap">
          <table className="voucher-table fixed-asset-accounting-table">
            <thead>
              <tr>
                <th>资产</th>
                <th>正式状态</th>
                <th>资本化分录</th>
                <th>最近折旧</th>
                <th>减值准备</th>
                <th>正式净值</th>
                <th>处置分录</th>
              </tr>
            </thead>
            <tbody>
              {formalCards.length ? formalCards.map((card) => (
                <tr key={card.asset_id}>
                  <td>
                    <strong>{card.asset_code}</strong>
                    <span>{card.asset_name}</span>
                  </td>
                  <td>{formalStatusLabel(card)}</td>
                  <td>{card.capitalization_entry_id ?? "未生成"}</td>
                  <td>{card.last_depreciated_period ?? "未计提"}</td>
                  <td>{money(card.impairment_amount)}</td>
                  <td>{money(card.net_book_value)}</td>
                  <td>{card.disposal_entry_ids.length ? card.disposal_entry_ids.join("、") : "未处置"}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={7}>暂无正式固定资产核算卡片</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <div className="fixed-asset-forms">
        <form className="fixed-asset-form" onSubmit={handleCreate}>
          <label>资产名称<input value={form.name} onChange={(event) => updateAssetField("name", event.target.value)} /></label>
          <label>类别<input value={form.category} onChange={(event) => updateAssetField("category", event.target.value)} /></label>
          <label>购置日期<input type="date" value={form.acquisition_date} onChange={(event) => updateAssetField("acquisition_date", event.target.value)} /></label>
          <label>原值<input type="number" min="0" value={form.original_cost} onChange={(event) => updateAssetField("original_cost", event.target.value)} /></label>
          <label>残值<input type="number" min="0" value={form.salvage_value} onChange={(event) => updateAssetField("salvage_value", event.target.value)} /></label>
          <label>折旧月数<input type="number" min="1" value={form.useful_life_months} onChange={(event) => updateAssetField("useful_life_months", event.target.value)} /></label>
          <label>位置<input value={form.location} onChange={(event) => updateAssetField("location", event.target.value)} /></label>
          <label>保管人<input value={form.custodian} onChange={(event) => updateAssetField("custodian", event.target.value)} /></label>
          <button type="submit" disabled={isBusy}>新增资产</button>
        </form>

        <section className="fixed-asset-form fixed-asset-inventory-form" aria-label="固定资产盘点表单">
          <label>盘点日期<input type="date" value={inventoryForm.inventory_date} onChange={(event) => updateInventoryField("inventory_date", event.target.value)} /></label>
          <label>位置<input value={inventoryForm.location} onChange={(event) => updateInventoryField("location", event.target.value)} /></label>
          <label>保管人<input value={inventoryForm.custodian} onChange={(event) => updateInventoryField("custodian", event.target.value)} /></label>
          <label>状态<input value={inventoryForm.condition} onChange={(event) => updateInventoryField("condition", event.target.value)} /></label>
          <label>盘点人<input value={inventoryForm.operator ?? ""} onChange={(event) => updateInventoryField("operator", event.target.value)} /></label>
          <label>备注<input value={inventoryForm.note ?? ""} onChange={(event) => updateInventoryField("note", event.target.value)} /></label>
          <button type="button" className="button-secondary" onClick={handleInventory} disabled={isBusy || !selectedAsset}>
            更新盘点
          </button>
        </section>
      </div>
    </section>
  );
}
