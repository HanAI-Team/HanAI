from pydantic import BaseModel


# 결제 준비 요청 (프론트 → 백엔드)
class PaymentPrepareRequest(BaseModel):
    tier: str           # "basic" / "premium"
    billing_period: str # "monthly" / "yearly"


# 결제 준비 응답 (백엔드 → 프론트)
class PaymentPrepareResponse(BaseModel):
    order_id: str       # 우리가 생성한 주문번호
    amount: int         # 실제 결제 금액 (원)
    order_name: str     # 결제창에 보일 상품명 예: "Zinmac 베이직 월간"


# 결제 확인 요청 (프론트 → 백엔드, 토스 successUrl 리다이렉트 후)
class PaymentConfirmRequest(BaseModel):
    payment_key: str    # 토스가 준 결제 키
    order_id: str       # 준비 단계에서 만든 주문번호
    amount: int         # 결제 금액 (검증용)


# 결제 확인 응답
class PaymentConfirmResponse(BaseModel):
    success: bool
    tier: str
    billing_period: str
    expired_at: str     # 구독 만료일
    message: str


# 토스페이먼츠 웹훅 payload
class TossWebhookPayload(BaseModel):
    event_type: str
    data: dict




TIER_CONFIG = {
    # 베타 가격
    ("basic_beta", "monthly"):   {"amount": 39_000,  "display_tier": "basic"},
    ("basic_beta", "yearly"):    {"amount": 389_000, "display_tier": "basic"},
    ("premium_beta", "monthly"): {"amount": 99_000,  "display_tier": "premium"},
    ("premium_beta", "yearly"):  {"amount": 986_400, "display_tier": "premium"},
    # 정식 가격 (심사 통과 후 전환)
    ("basic", "monthly"):        {"amount": 79_000,  "display_tier": "basic"},
    ("basic", "yearly"):         {"amount": 789_600, "display_tier": "basic"},
    ("premium", "monthly"):      {"amount": 159_000, "display_tier": "premium"},
    ("premium", "yearly"):       {"amount": 1_590_000, "display_tier": "premium"},

}

ORDER_NAME_TABLE = {
    ("basic_beta", "monthly"):   "Zinmac 베이직 월간 (베타)",
    ("basic_beta", "yearly"):    "Zinmac 베이직 연간 (베타)",
    ("premium_beta", "monthly"): "Zinmac 프리미엄 월간 (베타)",
    ("premium_beta", "yearly"):  "Zinmac 프리미엄 연간 (베타)",
    ("basic", "monthly"):        "Zinmac 베이직 월간",
    ("basic", "yearly"):         "Zinmac 베이직 연간",
    ("premium", "monthly"):      "Zinmac 프리미엄 월간",
    ("premium", "yearly"):       "Zinmac 프리미엄 연간",
}