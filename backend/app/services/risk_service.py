from app.models.finance import MonthlyFinanceRecord, RiskItem


COMPLIANCE_NOTE = "建议财务人员结合企业实际业务、申报口径和最新政策进一步复核。"


def _find_record(period: str, records: list[MonthlyFinanceRecord]) -> MonthlyFinanceRecord:
    for record in records:
        if record.period == period:
            return record
    available = ", ".join(record.period for record in records)
    raise ValueError(f"未找到期间 {period}，可用期间：{available}")


def _risk_level_label(level: int) -> str:
    labels = {
        1: "低风险",
        2: "关注",
        3: "需复核",
        4: "高风险",
        5: "严重风险",
    }
    return labels[level]


def detect_risks(period: str, records: list[MonthlyFinanceRecord]) -> list[RiskItem]:
    current = _find_record(period, records)
    risks: list[RiskItem] = []

    expense_rate = (
        current.sales_expense
        + current.admin_expense
        + current.rd_expense
        + current.finance_expense
    ) / current.revenue
    cash_profit_ratio = (
        current.operating_cash_flow_net / current.net_profit if current.net_profit else 0
    )
    gross_margin = (current.revenue - current.cost) / current.revenue

    if expense_rate >= 0.14:
        risks.append(
            RiskItem(
                id="expense-rate-review",
                title="费用率异常",
                level=3,
                level_label=_risk_level_label(3),
                description="本期期间费用率处于较高水平，可能压缩经营利润。",
                trigger_reason=f"期间费用率为 {expense_rate:.1%}，达到需复核阈值。",
                suggested_checks=["销售费用明细", "管理费用审批记录", "研发费用归集口径"],
                compliance_note=COMPLIANCE_NOTE,
            )
        )

    if cash_profit_ratio < 0.8:
        risks.append(
            RiskItem(
                id="cash-profit-divergence",
                title="现金流与利润背离",
                level=4,
                level_label=_risk_level_label(4),
                description="经营现金流净额低于净利润，利润质量需要进一步复核。",
                trigger_reason=f"经营现金流/净利润为 {cash_profit_ratio:.1%}，低于 80%。",
                suggested_checks=["应收账款账龄表", "期后回款记录", "大额客户信用政策"],
                compliance_note=COMPLIANCE_NOTE,
            )
        )

    if current.inventory_turnover_days >= 70:
        risks.append(
            RiskItem(
                id="inventory-turnover-review",
                title="库存周转异常",
                level=3,
                level_label=_risk_level_label(3),
                description="库存周转天数偏长，可能影响资金占用和存货跌价风险。",
                trigger_reason=f"库存周转天数为 {current.inventory_turnover_days:.0f} 天。",
                suggested_checks=["库存库龄表", "滞销品清单", "存货跌价准备测算表"],
                compliance_note=COMPLIANCE_NOTE,
            )
        )

    if current.tax_burden_rate < 0.04:
        risks.append(
            RiskItem(
                id="tax-burden-review",
                title="税负率需复核",
                level=3,
                level_label=_risk_level_label(3),
                description="税负率低于示例行业观察区间，建议复核申报口径。",
                trigger_reason=f"税负率为 {current.tax_burden_rate:.1%}。",
                suggested_checks=[
                    "增值税申报表",
                    "企业所得税预缴申报表",
                    "收入确认与发票开具匹配表",
                ],
                compliance_note=COMPLIANCE_NOTE,
            )
        )

    if gross_margin < 0.2:
        risks.append(
            RiskItem(
                id="gross-margin-review",
                title="毛利率异常",
                level=3,
                level_label=_risk_level_label(3),
                description="毛利率低于经营观察阈值，建议复核成本结转。",
                trigger_reason=f"毛利率为 {gross_margin:.1%}。",
                suggested_checks=["主营业务成本明细", "采购价格变动表", "成本结转凭证"],
                compliance_note=COMPLIANCE_NOTE,
            )
        )

    return risks
