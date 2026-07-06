from app.models.ecommerce import ECommerceProfitRequest
from app.services.ecommerce_profit_service import analyze_ecommerce_profit


def _sample_request() -> ECommerceProfitRequest:
    return ECommerceProfitRequest(
        period="2026-06",
        platform="天猫旗舰店",
        gmv=100000,
        refund_amount=8000,
        product_cost=48000,
        platform_commission=5500,
        payment_fee=600,
        advertising_spend=18000,
        logistics_cost=5200,
        packaging_cost=1200,
        labor_cost=4000,
        other_cost=1800,
        order_count=2000,
        visitor_count=50000,
    )


def test_analyze_ecommerce_profit_calculates_profit_metrics_and_risks():
    result = analyze_ecommerce_profit(_sample_request())

    assert result.net_sales == 92000
    assert result.gross_profit == 44000
    assert result.contribution_profit == 13500
    assert result.net_profit == 7700
    assert round(result.net_margin, 4) == 0.0837
    assert round(result.ad_spend_rate, 4) == 0.1957
    assert round(result.roi, 2) == 5.11
    assert result.average_order_value == 50
    assert result.metrics[0].title == "净销售额"
    assert result.cost_breakdown[0].name == "商品成本"
    assert result.profit_bridge[-1].name == "净利润"
    assert "high_ad_spend_rate" in {risk.id for risk in result.risks}
    assert "thin_net_margin" in {risk.id for risk in result.risks}


def test_analyze_ecommerce_profit_handles_zero_ad_spend_without_division_error():
    request = _sample_request().model_copy(update={"advertising_spend": 0})

    result = analyze_ecommerce_profit(request)

    assert result.roi == 0
    assert "high_ad_spend_rate" not in {risk.id for risk in result.risks}
