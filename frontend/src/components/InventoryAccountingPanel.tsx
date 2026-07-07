import { useEffect, useMemo, useState } from "react";
import {
  fetchInventoryAccountingBalances,
  postInventoryPurchaseReceipt,
  postInventorySalesIssue,
  recordInventoryCountVariance,
  recordInventoryImpairment
} from "../services/dashboardApi";
import type {
  InventoryAccountingSummary,
  InventoryBalance,
  InventoryMovement,
  InventoryMovementType
} from "../types/inventoryAccounting";

interface InventoryAccountingPanelProps {
  period: string;
}

const movementLabels: Record<InventoryMovementType, string> = {
  purchase_receipt: "采购入库",
  sales_issue: "销售出库",
  sales_return: "销售退回",
  purchase_return: "采购退回",
  adjustment_in: "盘盈调整",
  adjustment_out: "盘亏调整"
};

function money(value: string | number | null | undefined) {
  return Number(value ?? 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function quantity(value: string | number | null | undefined) {
  return Number(value ?? 0).toLocaleString("zh-CN", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
}

function movementLabel(type: InventoryMovementType) {
  return movementLabels[type] ?? type;
}

export default function InventoryAccountingPanel({ period }: InventoryAccountingPanelProps) {
  const [selectedPeriod, setSelectedPeriod] = useState(period);
  const [summary, setSummary] = useState<InventoryAccountingSummary | null>(null);
  const [skuId, setSkuId] = useState("SKU-001");
  const [warehouseId, setWarehouseId] = useState("WH-SH");
  const [supplierId, setSupplierId] = useState("SUP-001");
  const [quantityValue, setQuantityValue] = useState("10");
  const [amountValue, setAmountValue] = useState("1000.00");
  const [issueQuantity, setIssueQuantity] = useState("3");
  const [impairmentAmount, setImpairmentAmount] = useState("500.00");
  const [actualQuantity, setActualQuantity] = useState("6");
  const [lastAction, setLastAction] = useState("inventory_cost_rollforward");
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const balances = summary?.balances ?? [];
  const movements = summary?.movements ?? [];
  const selectedBalance = balances.find((balance) => balance.sku_id === skuId && balance.warehouse_id === warehouseId) ?? null;
  const salesIssueMovements = movements.filter((movement) => movement.movement_type === "sales_issue");
  const cogsAmount = useMemo(
    () => salesIssueMovements.reduce((total, movement) => total + Number(movement.amount ?? 0), 0),
    [salesIssueMovements]
  );
  const riskStatus = useMemo(() => {
    if (movements.some((movement) => movement.movement_type === "adjustment_out")) {
      return "盘亏已入账";
    }
    if (movements.some((movement) => movement.movement_type === "adjustment_in")) {
      return "盘盈已入账";
    }
    return lastAction.includes("跌价") ? "跌价已入账" : "正常";
  }, [lastAction, movements]);

  useEffect(() => {
    setSelectedPeriod(period);
  }, [period]);

  useEffect(() => {
    refreshSummary();
  }, []);

  function refreshSummary() {
    return fetchInventoryAccountingBalances("default")
      .then(setSummary)
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "存货核算读取失败"));
  }

  function runAction(action: () => Promise<unknown>, label: string) {
    setIsBusy(true);
    setError(null);
    action()
      .then(() => {
        setLastAction(label);
        return refreshSummary();
      })
      .catch((actionError) => setError(actionError instanceof Error ? actionError.message : `${label}失败`))
      .finally(() => setIsBusy(false));
  }

  function handlePurchaseReceipt() {
    runAction(
      () => postInventoryPurchaseReceipt({
        account_set_id: "default",
        sku_id: skuId,
        warehouse_id: warehouseId,
        period: selectedPeriod,
        quantity: quantityValue,
        amount: amountValue,
        supplier_id: supplierId
      }),
      "采购入库"
    );
  }

  function handleSalesIssue() {
    runAction(
      () => postInventorySalesIssue({
        account_set_id: "default",
        sku_id: skuId,
        warehouse_id: warehouseId,
        period: selectedPeriod,
        quantity: issueQuantity
      }),
      "销售出库"
    );
  }

  function handleImpairment() {
    runAction(
      () => recordInventoryImpairment({
        account_set_id: "default",
        sku_id: skuId,
        period: selectedPeriod,
        amount: impairmentAmount
      }),
      "跌价准备"
    );
  }

  function handleCountVariance() {
    runAction(
      () => recordInventoryCountVariance({
        account_set_id: "default",
        sku_id: skuId,
        warehouse_id: warehouseId,
        period: selectedPeriod,
        actual_quantity: actualQuantity,
        approved_by: "controller",
        approved_at: `${selectedPeriod}-30T10:00:00Z`
      }),
      "盘点差异"
    );
  }

  return (
    <section id="inventory-accounting-panel" className="inventory-accounting-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">存货正式核算</span>
          <h2>SKU 余额、出库成本与盘点差异</h2>
        </div>
        <div className="qa-status-strip">
          <span>{selectedPeriod}</span>
          <span>{lastAction}</span>
          <span>{riskStatus}</span>
        </div>
      </div>

      {error ? <p className="inline-error">{error}</p> : null}

      <div className="period-close-toolbar inventory-accounting-toolbar">
        <label>
          <span>期间</span>
          <input value={selectedPeriod} onChange={(event) => setSelectedPeriod(event.target.value)} />
        </label>
        <label>
          <span>SKU</span>
          <input value={skuId} onChange={(event) => setSkuId(event.target.value)} />
        </label>
        <label>
          <span>仓库</span>
          <input value={warehouseId} onChange={(event) => setWarehouseId(event.target.value)} />
        </label>
        <label>
          <span>供应商</span>
          <input value={supplierId} onChange={(event) => setSupplierId(event.target.value)} />
        </label>
        <button type="button" className="button-secondary" onClick={() => refreshSummary()} disabled={isBusy}>
          刷新
        </button>
      </div>

      <div className="period-close-toolbar inventory-accounting-actionbar">
        <label>
          <span>入库数量</span>
          <input value={quantityValue} onChange={(event) => setQuantityValue(event.target.value)} />
        </label>
        <label>
          <span>入库金额</span>
          <input value={amountValue} onChange={(event) => setAmountValue(event.target.value)} />
        </label>
        <button type="button" onClick={handlePurchaseReceipt} disabled={isBusy}>采购入库</button>
        <label>
          <span>出库数量</span>
          <input value={issueQuantity} onChange={(event) => setIssueQuantity(event.target.value)} />
        </label>
        <button type="button" onClick={handleSalesIssue} disabled={isBusy}>销售出库</button>
        <label>
          <span>跌价金额</span>
          <input value={impairmentAmount} onChange={(event) => setImpairmentAmount(event.target.value)} />
        </label>
        <button type="button" className="button-secondary" onClick={handleImpairment} disabled={isBusy}>跌价入账</button>
        <label>
          <span>实盘数量</span>
          <input value={actualQuantity} onChange={(event) => setActualQuantity(event.target.value)} />
        </label>
        <button type="button" className="button-secondary" onClick={handleCountVariance} disabled={isBusy}>盘点入账</button>
      </div>

      <div className="period-close-summary-grid inventory-accounting-summary-grid">
        <article>
          <span>库存数量</span>
          <strong>{quantity(selectedBalance?.quantity)}</strong>
        </article>
        <article>
          <span>库存金额</span>
          <strong>{money(selectedBalance?.amount)}</strong>
        </article>
        <article>
          <span>移动平均成本</span>
          <strong>{money(selectedBalance?.moving_average_cost)}</strong>
        </article>
        <article>
          <span>销售成本结转</span>
          <strong>{money(cogsAmount)}</strong>
        </article>
      </div>

      <div className="period-close-grid inventory-accounting-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">SKU 库存</span>
              <h3>余额与移动平均成本</h3>
            </div>
            <strong>{balances.length}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table inventory-accounting-balance-table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>仓库</th>
                  <th>数量</th>
                  <th>金额</th>
                  <th>移动平均</th>
                </tr>
              </thead>
              <tbody>
                {balances.length ? balances.map((balance: InventoryBalance) => (
                  <tr key={`${balance.sku_id}-${balance.warehouse_id}`}>
                    <td>{balance.sku_id}</td>
                    <td>{balance.warehouse_id}</td>
                    <td>{quantity(balance.quantity)}</td>
                    <td>{money(balance.amount)}</td>
                    <td>{money(balance.moving_average_cost)}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={5}>暂无库存余额</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">入库出库流水</span>
              <h3>存货核算移动</h3>
            </div>
            <strong>{movements.length}</strong>
          </div>
          <div className="voucher-table-wrap">
            <table className="voucher-table inventory-accounting-movement-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>类型</th>
                  <th>SKU</th>
                  <th>仓库</th>
                  <th>数量</th>
                  <th>金额</th>
                  <th>分录</th>
                </tr>
              </thead>
              <tbody>
                {movements.length ? movements.slice().reverse().map((movement: InventoryMovement) => (
                  <tr key={movement.movement_id}>
                    <td>{movement.movement_date}</td>
                    <td>{movementLabel(movement.movement_type)}</td>
                    <td>{movement.sku_id}</td>
                    <td>{movement.warehouse_id}</td>
                    <td>{quantity(movement.quantity)}</td>
                    <td>{money(movement.amount)}</td>
                    <td>{movement.journal_entry_id ?? "-"}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={7}>暂无存货流水</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>
  );
}
