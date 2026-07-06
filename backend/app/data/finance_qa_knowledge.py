from dataclasses import dataclass


@dataclass(frozen=True)
class FinanceKnowledgeCard:
    intent: str
    keywords: tuple[str, ...]
    answer: str
    action_items: tuple[str, ...]
    risk_level: str
    policy_ids: tuple[str, ...]


KNOWLEDGE_CARDS: tuple[FinanceKnowledgeCard, ...] = (
    FinanceKnowledgeCard(
        intent="revenue_recognition",
        keywords=("收入", "确认", "发货", "履约", "订单", "电商", "平台"),
        answer=(
            "收入确认应先判断合同及履约义务，再判断客户是否已取得相关商品控制权。"
            "电商订单通常不能只按下单或收款确认收入，应结合发货、签收、退货权、平台结算规则"
            "和企业会计政策判断。若存在无理由退货、质量保证、积分返利或平台代收代付，应同步评估"
            "可变对价、预计退款负债和合同负债。"
        ),
        action_items=(
            "核对订单、发货、签收、退货期和平台结算单，确认控制权转移时点。",
            "将退款、折扣、优惠券、积分、佣金和平台服务费与收入总额法/净额法判断一起复核。",
            "形成收入确认会计政策说明，保持同类交易口径一致。",
        ),
        risk_level="medium",
        policy_ids=("cas-14-revenue-2017",),
    ),
    FinanceKnowledgeCard(
        intent="fixed_asset",
        keywords=("固定资产", "折旧", "残值", "使用寿命", "资本化", "资产"),
        answer=(
            "固定资产处理应关注初始计量、后续折旧、减值迹象和处置。折旧方法、预计使用寿命、"
            "预计净残值一经确定，不应随意变更；确需变更时通常按会计估计变更处理，并保留审批"
            "和测算依据。维修支出是否资本化，应判断是否使资产未来经济利益增加。"
        ),
        action_items=(
            "核对资产验收单、发票、合同、付款和达到预定可使用状态的日期。",
            "复核折旧年限、残值率、折旧方法与企业会计政策是否一致。",
            "盘点闲置、毁损或盈利能力下降资产，必要时评估减值风险。",
        ),
        risk_level="medium",
        policy_ids=("cas-04-fixed-assets-2006",),
    ),
    FinanceKnowledgeCard(
        intent="invoice_risk",
        keywords=("发票", "电子发票", "虚开", "进项", "抵扣", "报销", "金税"),
        answer=(
            "发票风险应重点检查业务真实性、合同流、资金流、物流或服务交付记录是否一致。"
            "电子发票和纸质发票一样需要关注开票方、购买方、项目名称、税号、金额、税额、"
            "备注栏和红冲记录。仅有发票不能证明交易真实，异常供应商、集中开票、品名不符"
            "和资金回流都需要重点复核。"
        ),
        action_items=(
            "建立合同、订单、入库或验收、付款、发票的四流/五流核对清单。",
            "对高频小额、月底集中、跨区域异常供应商开票进行抽样复核。",
            "对拟抵扣进项发票保留业务真实性证据，异常项目先暂停抵扣并人工确认。",
        ),
        risk_level="high",
        policy_ids=("invoice-management-measures",),
    ),
)
