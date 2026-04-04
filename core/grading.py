"""Option contract grading and scoring.

Scores option contracts on open interest, volume, premium,
and days to expiry. Applies penalties for poor liquidity
or excessive OTM distance.
"""


def grade(
    premium: float,
    volume: int,
    oi: int,
    days: int,
    otm_pct: float,
    max_otm: float = 20.0,
) -> str:
    """Grade an option contract from A to D.

    Scoring breakdown (max 100):
        - Open interest: 10-25 points
        - Volume: 15-25 points
        - Premium sweetness: 15-25 points
        - Days to expiry: 15-25 points
        - Penalties for low OI (<10), low volume (<5), or OTM > max_otm

    Args:
        premium: Option premium per share.
        volume: Daily trading volume.
        oi: Open interest.
        days: Days to expiration.
        otm_pct: Percentage out of the money.
        max_otm: Maximum acceptable OTM percentage.

    Returns:
        Letter grade: "A" (>=70), "B" (>=55), "C" (>=40), or "D".
    """
    score = 0

    # Open interest scoring
    if oi > 500:
        score += 25
    elif oi > 100:
        score += 20
    elif oi > 50:
        score += 15
    elif oi > 20:
        score += 10

    # Volume scoring
    if volume > 200:
        score += 25
    elif volume > 50:
        score += 20
    elif volume > 20:
        score += 15

    # Premium sweetness (cheap options preferred)
    if 0.05 <= premium <= 0.50:
        score += 25
    elif 0.50 < premium <= 1.00:
        score += 20
    elif 1.00 < premium <= 1.50:
        score += 15

    # Days to expiry (30-60 is the sweet spot)
    if 30 <= days <= 60:
        score += 25
    elif 60 < days <= 90:
        score += 20
    elif 25 <= days < 30:
        score += 15

    # Penalties
    if oi < 10:
        score -= 20
    if volume < 5:
        score -= 15
    if otm_pct > max_otm:
        score -= 30

    if score >= 70:
        return "A"
    elif score >= 55:
        return "B"
    elif score >= 40:
        return "C"
    return "D"
