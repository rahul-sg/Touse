"""Per-loan-type affordability calculators.

Each function takes a body (AffordabilityRequest), the base_rate (decimal),
and a credit_premium (decimal), and returns a result dict.
"""

from typing import Any

CONFORMING_LIMIT = 766_550
FHA_LIMIT = 524_225


def _monthly_payment(principal: float, annual_rate: float, years: int = 30) -> float:
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def _max_loan_from_payment(monthly: float, annual_rate: float, years: int = 30) -> float:
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return monthly * n
    return monthly * ((1 + r) ** n - 1) / (r * (1 + r) ** n)


def calc_conventional(body: Any, base_rate: float, credit_premium: float) -> dict:
    rate = base_rate + credit_premium
    gross_monthly = body.annual_income / 12
    available = min(gross_monthly * 0.28, gross_monthly * 0.36 - body.monthly_debt)
    available = max(available, 1.0)

    tentative_loan = _max_loan_from_payment(available, rate)
    tentative_price = tentative_loan + body.down_payment
    dp_pct = body.down_payment / tentative_price if tentative_price > 0 else 0

    pmi_monthly = 0.0
    notes: list[str] = []

    if dp_pct < 0.20:
        pmi_monthly = tentative_loan * 0.008 / 12
        available = max(available - pmi_monthly, 1.0)
        notes.append(f"PMI ~${round(pmi_monthly)}/mo — drops when equity reaches 20%")

    max_loan = min(_max_loan_from_payment(available, rate), CONFORMING_LIMIT)
    if tentative_loan > CONFORMING_LIMIT:
        notes.append(f"Capped at conforming limit (${CONFORMING_LIMIT:,}) — consider Jumbo")

    max_price = max_loan + body.down_payment
    payment = _monthly_payment(max_loan, rate)
    bp_delta = (_max_loan_from_payment(available, rate + 0.005) + body.down_payment) - max_price

    result: dict = {
        "max_price": round(max_price),
        "max_loan": round(max_loan),
        "monthly_payment": round(payment + pmi_monthly),
        "rate_used": round(rate * 100, 3),
        "down_payment": body.down_payment,
        "buying_power_change_per_half_point": round(bp_delta),
        "loan_type": "conventional",
    }
    if pmi_monthly > 0:
        result["pmi_monthly"] = round(pmi_monthly)
    if notes:
        result["notes"] = notes
    return result


def calc_fha(body: Any, base_rate: float, credit_premium: float) -> dict:
    rate = base_rate + credit_premium
    gross_monthly = body.annual_income / 12
    # FHA DTI: 31% front-end, 43% back-end
    available = min(gross_monthly * 0.31, gross_monthly * 0.43 - body.monthly_debt)
    available = max(available, 1.0)

    # Iterate once: estimate loan, subtract MIP, recompute
    tentative_loan = _max_loan_from_payment(available, rate)
    mip_rate = 0.0055  # 0.55% annual for LTV > 90%, 30yr term
    mip_monthly = tentative_loan * mip_rate / 12
    available = max(available - mip_monthly, 1.0)

    max_loan = min(_max_loan_from_payment(available, rate), FHA_LIMIT)
    upfront_mip = max_loan * 0.0175  # 1.75% financed
    mip_monthly_final = max_loan * mip_rate / 12
    payment = _monthly_payment(max_loan + upfront_mip, rate) + mip_monthly_final

    max_price = max_loan + body.down_payment
    bp_delta = (min(_max_loan_from_payment(available, rate + 0.005), FHA_LIMIT) + body.down_payment) - max_price

    return {
        "max_price": round(max_price),
        "max_loan": round(max_loan),
        "monthly_payment": round(payment),
        "rate_used": round(rate * 100, 3),
        "down_payment": body.down_payment,
        "buying_power_change_per_half_point": round(bp_delta),
        "loan_type": "fha",
        "mip_monthly": round(mip_monthly_final),
        "upfront_mip_financed": round(upfront_mip),
        "notes": [
            f"FHA MIP: ${round(mip_monthly_final)}/mo + ${round(upfront_mip):,} upfront (financed)",
            f"FHA loan cap: ${FHA_LIMIT:,}",
        ],
    }


def calc_va(body: Any, base_rate: float, credit_premium: float) -> dict:
    rate = base_rate + credit_premium
    gross_monthly = body.annual_income / 12
    # VA: no front-end limit, 41% back-end
    available = max(gross_monthly * 0.41 - body.monthly_debt, 1.0)

    max_loan = _max_loan_from_payment(available, rate)
    tentative_price = max_loan + body.down_payment
    dp_pct = body.down_payment / tentative_price if tentative_price > 0 else 0
    funding_fee_pct = 0.0125 if dp_pct >= 0.10 else 0.0215
    funding_fee = max_loan * funding_fee_pct

    max_price = max_loan + body.down_payment
    payment = _monthly_payment(max_loan + funding_fee, rate)
    bp_delta = (_max_loan_from_payment(available, rate + 0.005) + body.down_payment) - max_price

    return {
        "max_price": round(max_price),
        "max_loan": round(max_loan),
        "monthly_payment": round(payment),
        "rate_used": round(rate * 100, 3),
        "down_payment": body.down_payment,
        "buying_power_change_per_half_point": round(bp_delta),
        "loan_type": "va",
        "funding_fee_financed": round(funding_fee),
        "notes": [
            f"VA funding fee: ${round(funding_fee):,} financed ({funding_fee_pct * 100:.2f}% of loan)",
            "No PMI required — available to eligible veterans and active-duty service members",
        ],
    }


def calc_usda(body: Any, base_rate: float, credit_premium: float) -> dict:
    rate = base_rate + credit_premium
    gross_monthly = body.annual_income / 12
    # USDA DTI: 29% front-end, 41% back-end
    available = min(gross_monthly * 0.29, gross_monthly * 0.41 - body.monthly_debt)
    available = max(available, 1.0)

    # Iterate once: estimate loan, subtract annual fee, recompute
    tentative_loan = _max_loan_from_payment(available, rate)
    usda_fee_rate = 0.0035  # 0.35% annual
    usda_fee_monthly = tentative_loan * usda_fee_rate / 12
    available = max(available - usda_fee_monthly, 1.0)

    max_loan = _max_loan_from_payment(available, rate)
    upfront_fee = max_loan * 0.01  # 1% guarantee fee, financed
    usda_fee_monthly_final = max_loan * usda_fee_rate / 12
    payment = _monthly_payment(max_loan + upfront_fee, rate) + usda_fee_monthly_final

    max_price = max_loan + body.down_payment
    bp_delta = (_max_loan_from_payment(available, rate + 0.005) + body.down_payment) - max_price

    return {
        "max_price": round(max_price),
        "max_loan": round(max_loan),
        "monthly_payment": round(payment),
        "rate_used": round(rate * 100, 3),
        "down_payment": body.down_payment,
        "buying_power_change_per_half_point": round(bp_delta),
        "loan_type": "usda",
        "usda_annual_fee_monthly": round(usda_fee_monthly_final),
        "notes": [
            f"USDA annual fee: ${round(usda_fee_monthly_final)}/mo + ${round(upfront_fee):,} upfront (financed)",
            "Rural properties only — 0% down payment required",
        ],
    }


def calc_arm_5_1(body: Any, base_rate: float, credit_premium: float) -> dict:
    # ARM 5/1: ~0.75% discount on initial rate vs 30yr fixed
    initial_rate = max(base_rate - 0.0075, 0.03) + credit_premium
    worst_rate = initial_rate + 0.05  # 5% lifetime rate cap

    gross_monthly = body.annual_income / 12
    available = min(gross_monthly * 0.28, gross_monthly * 0.36 - body.monthly_debt)
    available = max(available, 1.0)

    tentative_loan = _max_loan_from_payment(available, initial_rate)
    tentative_price = tentative_loan + body.down_payment
    dp_pct = body.down_payment / tentative_price if tentative_price > 0 else 0

    pmi_monthly = 0.0
    notes: list[str] = ["ARM 5/1: rate fixed 5 years, then adjusts annually (±2% annual cap, +5% lifetime)"]

    if dp_pct < 0.20:
        pmi_monthly = tentative_loan * 0.008 / 12
        available = max(available - pmi_monthly, 1.0)
        notes.append(f"PMI ~${round(pmi_monthly)}/mo — drops when equity reaches 20%")

    max_loan = min(_max_loan_from_payment(available, initial_rate), CONFORMING_LIMIT)
    max_price = max_loan + body.down_payment
    payment = _monthly_payment(max_loan, initial_rate)
    worst_payment = _monthly_payment(max_loan, worst_rate)
    bp_delta = (_max_loan_from_payment(available, initial_rate + 0.005) + body.down_payment) - max_price

    result: dict = {
        "max_price": round(max_price),
        "max_loan": round(max_loan),
        "monthly_payment": round(payment + pmi_monthly),
        "rate_used": round(initial_rate * 100, 3),
        "down_payment": body.down_payment,
        "buying_power_change_per_half_point": round(bp_delta),
        "loan_type": "arm_5_1",
        "arm_worst_case": {
            "rate_used": round(worst_rate * 100, 3),
            "monthly_payment": round(worst_payment + pmi_monthly),
        },
        "notes": notes,
    }
    if pmi_monthly > 0:
        result["pmi_monthly"] = round(pmi_monthly)
    return result


def calc_jumbo(body: Any, base_rate: float, credit_premium: float) -> dict:
    # Jumbo: +0.25% rate spread, 43% back-end DTI, no PMI
    rate = base_rate + credit_premium + 0.0025
    gross_monthly = body.annual_income / 12
    available = min(gross_monthly * 0.28, gross_monthly * 0.43 - body.monthly_debt)
    available = max(available, 1.0)

    max_loan = _max_loan_from_payment(available, rate)
    # Jumbo starts above conforming limit — ensure we're above it
    max_loan = max(max_loan, CONFORMING_LIMIT + 1)
    max_price = max_loan + body.down_payment
    payment = _monthly_payment(max_loan, rate)
    bp_delta = (_max_loan_from_payment(available, rate + 0.005) + body.down_payment) - max_price

    return {
        "max_price": round(max_price),
        "max_loan": round(max_loan),
        "monthly_payment": round(payment),
        "rate_used": round(rate * 100, 3),
        "down_payment": body.down_payment,
        "buying_power_change_per_half_point": round(bp_delta),
        "loan_type": "jumbo",
        "notes": [
            "No PMI — stricter underwriting applies",
            f"Loans above ${CONFORMING_LIMIT:,} conforming limit",
            "Typically requires 720+ credit score and 10-20% down",
        ],
    }


LOAN_CALCULATORS = {
    "conventional": calc_conventional,
    "fha": calc_fha,
    "va": calc_va,
    "usda": calc_usda,
    "arm_5_1": calc_arm_5_1,
    "jumbo": calc_jumbo,
}
