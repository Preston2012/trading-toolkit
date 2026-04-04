"""Position sizing and exit ladder generation.

Calculates contract quantities based on max risk per trade,
generates staged exit ladders, and sets kill prices.
Caps contracts to prevent illiquid penny-option positions.
"""

import logging
from typing import TypedDict

logger = logging.getLogger(__name__)

MAX_RISK_PCT = 0.03  # 3% of fund per trade
KILL_LOSS_PCT = 0.50  # Cut at 50% premium loss
MAX_CONTRACTS = 20  # Cap to prevent illiquid penny-option positions


class ExitTranche(TypedDict):
    """A single exit ladder tranche."""

    contracts: int
    target: str


class PositionResult(TypedDict):
    """Full position sizing output."""

    contracts: int
    total_cost: float
    pct_of_fund: float
    ladder: list[ExitTranche]
    kill_price: float


def build_ladder(contracts: int) -> list[ExitTranche]:
    """Generate exit ladder tranches based on contract count.

    Args:
        contracts: Total number of contracts in the position.

    Returns:
        List of ExitTranche dicts. 4 tranches for 8+, 3 for 4-7,
        2 for 2-3, single tranche for 1.
    """
    if contracts <= 0:
        return []
    if contracts == 1:
        return [{"contracts": 1, "target": "2-3x or let ride"}]
    if contracts >= 8:
        t1 = int(contracts * 0.25)
        t2 = int(contracts * 0.25)
        t3 = int(contracts * 0.25)
        t4 = contracts - t1 - t2 - t3
        return [
            {"contracts": t1, "target": "2x (recover basis)"},
            {"contracts": t2, "target": "3-4x (lock profit)"},
            {"contracts": t3, "target": "6-8x (let run)"},
            {"contracts": t4, "target": "10x+ (moon bag)"},
        ]
    elif contracts >= 4:
        t1 = int(contracts * 0.33)
        t2 = int(contracts * 0.33)
        t3 = contracts - t1 - t2
        return [
            {"contracts": t1, "target": "2x (recover basis)"},
            {"contracts": t2, "target": "4-5x (lock profit)"},
            {"contracts": t3, "target": "8x+ (moon bag)"},
        ]
    else:
        t1 = contracts // 2
        t2 = contracts - t1
        return [
            {"contracts": t1, "target": "2x (recover basis)"},
            {"contracts": t2, "target": "5x+ (let ride)"},
        ]


def calc_position(
    premium: float,
    price: float,
    strike: float,
    days: int,
    trade_fund: float = 3000.0,
    side: str = "call",
) -> PositionResult:
    """Calculate position size and exit strategy.

    Uses 3% max risk per play to determine contract count,
    then generates a staged exit ladder and kill price.
    Caps at MAX_CONTRACTS to prevent illiquid positions.

    Args:
        premium: Option premium per share.
        price: Current underlying price.
        strike: Option strike price.
        days: Days to expiration.
        trade_fund: Total trading fund size.
        side: "call" or "put".

    Returns:
        PositionResult with contracts, cost, ladder, and kill price.
    """
    # Guard against zero or negative premium (data error)
    if premium <= 0:
        logger.warning("Invalid premium %.4f, defaulting to 1 contract", premium)
        return PositionResult(
            contracts=1,
            total_cost=0.0,
            pct_of_fund=0.0,
            ladder=[{"contracts": 1, "target": "2-3x or let ride"}],
            kill_price=0.0,
        )

    max_risk = trade_fund * MAX_RISK_PCT
    cost_per_contract = premium * 100
    contracts = max(1, min(int(max_risk / cost_per_contract), MAX_CONTRACTS))
    total_cost = round(contracts * cost_per_contract, 2)
    pct_of_fund = round(total_cost / trade_fund * 100, 1)

    ladder = build_ladder(contracts)
    kill_price = round(premium * KILL_LOSS_PCT, 2)

    return PositionResult(
        contracts=contracts,
        total_cost=total_cost,
        pct_of_fund=pct_of_fund,
        ladder=ladder,
        kill_price=kill_price,
    )
