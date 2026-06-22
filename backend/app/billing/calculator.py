from datetime import date
from decimal import ROUND_UP, Decimal

from app.billing.pediatric_dosage import get_max_allowed_ratio


def calculate_prescription_price(
    unit_price: int,
    daily_dosage_ratio: Decimal,
    total_dosage_days: int,
    birth_date: date | None = None,
)-> int:
    #    공식: unit_price × daily_dosage_ratio × total_dosage_days 그치만만 얼라면 할인 
    ratio = Decimal(str(daily_dosage_ratio))

    if birth_date:
        pediatric_ratio = Decimal(str(get_max_allowed_ratio(birth_date)))
        ratio = min(daily_dosage_ratio, pediatric_ratio)
    
    total = Decimal(str(unit_price)) * ratio * Decimal(str(total_dosage_days))
    return int(total.quantize(Decimal("1"), rounding=ROUND_UP))



def validate_prescription_limits(
    prescription_type: str,
    species_count: int,
    total_weight_g: Decimal,
    total_dosage_price: int,
    birth_date: date | None = None,
) -> list[dict]:
    violations=[]
    ratio = Decimal(str(get_max_allowed_ratio(birth_date))) if birth_date else Decimal("1.0")

    if prescription_type == "가감처방":
        max_species = 5
        max_weight_g = Decimal("10.0") * ratio
        if species_count > max_species:
            violations.append({
                "rule": "가감처방 종수 초과",
                "detail": f"가미 약재는 {max_species}종 이하여야 합니다. (현재 {species_count}종)"
            })
        if total_weight_g > max_weight_g:
            violations.append({
                "rule": "가감처방 용량 초과",
                "detail": f"가미 약재 총 용량이 {max_weight_g}g을 초과합니다. (현재 {total_weight_g}g)"
            })

    elif prescription_type == "임의처방":
        max_species = 15
        max_weight_g = Decimal("50.0") * ratio
        max_price = int(Decimal("3000") * ratio)
        if species_count > max_species:
            violations.append({
                "rule": "임의처방 종수 초과",
                "detail": f"임의처방은 {max_species}종 이하여야 합니다. (현재 {species_count}종)"
            })
        if total_weight_g > max_weight_g:
            violations.append({
                "rule": "임의처방 용량 초과",
                "detail": f"총 용량이 {max_weight_g}g을 초과합니다. (현재 {total_weight_g}g)"
            })
        if total_dosage_price > max_price:
            violations.append({
                "rule": "임의처방 비용 초과",
                "detail": f"임의처방 비용이 {max_price}원을 초과합니다. (현재 {total_dosage_price}원)"
            })

    return violations

