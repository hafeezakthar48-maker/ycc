from app.models.ecommerce import (
    ECommerceChartPoint,
    ECommerceMetric,
    ECommerceProfitRequest,
    ECommerceProfitResult,
    ECommerceRiskItem,
)


def analyze_ecommerce_profit(request: ECommerceProfitRequest) -> ECommerceProfitResult:
    net_sales = max(request.gmv - request.refund_amount, 0)
    gross_profit = net_sales - request.product_cost
    contribution_profit = (
        net_sales
        - request.product_cost
        - request.platform_commission
        - request.payment_fee
        - request.advertising_spend
        - request.logistics_cost
        - request.packaging_cost
    )
    net_profit = contribution_profit - request.labor_cost - request.other_cost
    gross_margin = _safe_divide(gross_profit, net_sales)
    net_margin = _safe_divide(net_profit, net_sales)
    ad_spend_rate = _safe_divide(request.advertising_spend, net_sales)
    roi = _safe_divide(net_sales, request.advertising_spend)
    refund_rate = _safe_divide(request.refund_amount, request.gmv)
    average_order_value = _safe_divide(request.gmv, request.order_count)
    conversion_rate = _safe_divide(request.order_count, request.visitor_count)
    risks = _detect_ecommerce_risks(net_margin, ad_spend_rate, refund_rate, conversion_rate)

    return ECommerceProfitResult(
        period=request.period,
        platform=request.platform,
        net_sales=round(net_sales, 2),
        gross_profit=round(gross_profit, 2),
        contribution_profit=round(contribution_profit, 2),
        net_profit=round(net_profit, 2),
        gross_margin=round(gross_margin, 6),
        net_margin=round(net_margin, 6),
        ad_spend_rate=round(ad_spend_rate, 6),
        roi=round(roi, 6),
        refund_rate=round(refund_rate, 6),
        average_order_value=round(average_order_value, 2),
        conversion_rate=round(conversion_rate, 6),
        metrics=_build_metrics(net_sales, net_profit, net_margin, roi, refund_rate),
        cost_breakdown=_build_cost_breakdown(request),
        profit_bridge=_build_profit_bridge(net_sales, request, net_profit),
        risks=risks,
        suggestions=_build_suggestions(risks),
    )


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0


def _currency(value: float) -> str:
    return f"¥{value:,.0f}"


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _build_metrics(
    net_sales: float,
    net_profit: float,
    net_margin: float,
    roi: float,
    refund_rate: float,
) -> list[ECommerceMetric]:
    return [
        ECommerceMetric(
            key="net_sales",
            title="净销售额",
            value=_currency(net_sales),
            status="normal",
        ),
        ECommerceMetric(
            key="net_profit",
            title="净利润",
            value=_currency(net_profit),
            status="danger" if net_profit < 0 else "warning" if net_margin < 0.1 else "normal",
        ),
        ECommerceMetric(
            key="net_margin",
            title="净利率",
            value=_percent(net_margin),
            status="warning" if net_margin < 0.1 else "normal",
        ),
        ECommerceMetric(
            key="roi",
            title="投放 ROI",
            value=f"{roi:.2f}",
            status="warning" if 0 < roi < 4 else "normal",
        ),
        ECommerceMetric(
            key="refund_rate",
            title="退款率",
            value=_percent(refund_rate),
            status="warning" if refund_rate > 0.08 else "normal",
        ),
    ]


def _build_cost_breakdown(request: ECommerceProfitRequest) -> list[ECommerceChartPoint]:
    return [
        ECommerceChartPoint(name="商品成本", value=request.product_cost),
        ECommerceChartPoint(name="广告投放", value=request.advertising_spend),
        ECommerceChartPoint(name="平台佣金", value=request.platform_commission),
        ECommerceChartPoint(name="物流成本", value=request.logistics_cost),
        ECommerceChartPoint(name="支付手续费", value=request.payment_fee),
        ECommerceChartPoint(name="包装成本", value=request.packaging_cost),
        ECommerceChartPoint(name="人工成本", value=request.labor_cost),
        ECommerceChartPoint(name="其他成本", value=request.other_cost),
    ]


def _build_profit_bridge(
    net_sales: float,
    request: ECommerceProfitRequest,
    net_profit: float,
) -> list[ECommerceChartPoint]:
    return [
        ECommerceChartPoint(name="净销售额", value=net_sales),
        ECommerceChartPoint(name="商品成本", value=-request.product_cost),
        ECommerceChartPoint(name="平台佣金", value=-request.platform_commission),
        ECommerceChartPoint(name="支付手续费", value=-request.payment_fee),
        ECommerceChartPoint(name="广告投放", value=-request.advertising_spend),
        ECommerceChartPoint(name="物流包装", value=-(request.logistics_cost + request.packaging_cost)),
        ECommerceChartPoint(name="人工及其他", value=-(request.labor_cost + request.other_cost)),
        ECommerceChartPoint(name="净利润", value=net_profit),
    ]


def _detect_ecommerce_risks(
    net_margin: float,
    ad_spend_rate: float,
    refund_rate: float,
    conversion_rate: float,
) -> list[ECommerceRiskItem]:
    risks: list[ECommerceRiskItem] = []
    if ad_spend_rate > 0.15:
        risks.append(
            ECommerceRiskItem(
                id="high_ad_spend_rate",
                title="广告费率偏高",
                level=4,
                description=f"广告投放占净销售额 {_percent(ad_spend_rate)}，需要复核投放效率。",
                suggestion="按渠道拆分 ROI，暂停低转化计划，复核达人佣金和直通车关键词成本。",
            )
        )
    if net_margin < 0.1:
        risks.append(
            ECommerceRiskItem(
                id="thin_net_margin",
                title="净利率偏薄",
                level=4,
                description=f"净利率仅 {_percent(net_margin)}，利润缓冲不足。",
                suggestion="复核售价、商品成本、平台扣点、促销折扣和物流补贴，优先保住核心 SKU 毛利。",
            )
        )
    if refund_rate > 0.08:
        risks.append(
            ECommerceRiskItem(
                id="high_refund_rate",
                title="退款率偏高",
                level=3,
                description=f"退款率为 {_percent(refund_rate)}，可能侵蚀真实收入。",
                suggestion="按 SKU、主播、活动批次拆分退款原因，关注质量、尺码、承诺不一致等问题。",
            )
        )
    if 0 < conversion_rate < 0.03:
        risks.append(
            ECommerceRiskItem(
                id="low_conversion_rate",
                title="转化率偏低",
                level=3,
                description=f"访客到订单转化率为 {_percent(conversion_rate)}。",
                suggestion="复核详情页、价格带、客服响应、优惠券门槛和流量来源质量。",
            )
        )
    return risks


def _build_suggestions(risks: list[ECommerceRiskItem]) -> list[str]:
    base = [
        "按平台、店铺、SKU 和投放渠道建立日维度利润表，避免只看 GMV。",
        "把退款、平台扣点、达人佣金、运费险和售后补贴纳入净利润口径。",
        "将电商收入、平台服务费、广告费和物流费与发票、回款流水定期核对。",
    ]
    return [risk.suggestion for risk in risks] + base
