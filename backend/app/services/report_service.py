from app.data.sample_finance_data import SAMPLE_FINANCE_DATA
from app.models.finance import ManagementReport, MonthlyFinanceRecord, ReportSection
from app.services.analysis_service import COMPANY_NAME, build_dashboard_overview


def build_management_report(period: str) -> ManagementReport:
    return build_management_report_from_records(period, SAMPLE_FINANCE_DATA)


def build_management_report_from_records(
    period: str, records: list[MonthlyFinanceRecord]
) -> ManagementReport:
    overview = build_dashboard_overview(period, records)
    risk_titles = (
        "、".join(risk.title for risk in overview.risks)
        if overview.risks
        else "未发现需重点复核事项"
    )

    return ManagementReport(
        period=period,
        company_name=COMPANY_NAME,
        title=f"{COMPANY_NAME}{period}经营分析报告草稿",
        sections=[
            ReportSection(
                title="利润分析",
                content="本期收入、成本和净利润保持增长，但期间费用率需要结合预算和业务扩张情况复核。",
            ),
            ReportSection(
                title="资金分析",
                content="经营现金流低于净利润，建议关注应收账款期后回款、客户信用政策和现金流预测。",
            ),
            ReportSection(
                title="风险提示",
                content=f"系统识别的重点复核事项包括：{risk_titles}。这些内容仅作为经营与财税风险提示。",
            ),
            ReportSection(
                title="管理建议",
                content="建议财务经理组织销售、采购、仓储和税务岗位复核费用、回款、库存和申报口径。",
            ),
        ],
    )
