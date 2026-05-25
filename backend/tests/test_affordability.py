from app.services.affordability import _credit_score_premium
from app.services.loan_calculators import (
    _monthly_payment,
    _max_loan_from_payment,
)


def test_monthly_payment_known_value():
    # $400k loan at 7% for 30 years ≈ $2,661/mo
    payment = _monthly_payment(400_000, 0.07)
    assert 2650 < payment < 2680


def test_max_loan_roundtrip():
    rate = 0.068
    payment = _monthly_payment(300_000, rate)
    recovered = _max_loan_from_payment(payment, rate)
    assert abs(recovered - 300_000) < 1  # within $1


def test_credit_score_premium_tiers():
    assert _credit_score_premium(800) == 0.0
    assert _credit_score_premium(720) == 0.003
    assert _credit_score_premium(670) == 0.008
    assert _credit_score_premium(580) == 0.04  # below all tiers → penalty


def test_monthly_payment_zero_rate():
    # Edge case: 0% rate
    payment = _monthly_payment(120_000, 0.0, years=10)
    assert abs(payment - 1_000) < 0.01  # exactly $1,000/mo
