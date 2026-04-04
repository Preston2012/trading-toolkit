"""Macro thesis maps for options scanning.

Each ETF has directional theses (call/put), catalyst triggers,
and filtering parameters for the scanner.
"""

from typing import TypedDict


class ThesisConfig(TypedDict):
    """Configuration for a single ETF thesis."""

    call: str
    put: str
    catalyst: str
    max_otm: int
    min_vol: int
    min_oi: int
    beta: float


THESIS_MAP: dict[str, ThesisConfig] = {
    "XLE": {
        "call": "Oil war escalation. Hormuz closed, Houthis active. $110 WTI = XLE $70+",
        "put": "Ceasefire/peace = oil crashes 20% = XLE drops to $52-55",
        "catalyst": "Apr 6 Trump deadline, Kharg Island, ceasefire talks",
        "max_otm": 15, "min_vol": 20, "min_oi": 50, "beta": 1.2,
    },
    "JETS": {
        "call": "Peace hedge. Ceasefire = oil crashes = airlines surge 20-30%",
        "put": "War extends = jet fuel $7+ = airlines bleed another 15%",
        "catalyst": "Iran deal/ceasefire, jet fuel prices, airline guidance",
        "max_otm": 25, "min_vol": 15, "min_oi": 30, "beta": 1.5,
    },
    "TLT": {
        "call": "Oil kills economy -> recession -> Fed cuts -> bonds rip 8-12%",
        "put": "Inflation stays hot from oil -> Fed holds -> bonds drop 5%",
        "catalyst": "FOMC Apr 28-29, CPI, recession signals",
        "max_otm": 10, "min_vol": 50, "min_oi": 50, "beta": 0.8,
    },
    "XBI": {
        "call": "Biotech FDA binary. ONLY with known PDUFA date",
        "put": "Rate fear selloff crushes speculative biotech",
        "catalyst": "FDA PDUFA dates ONLY",
        "max_otm": 15, "min_vol": 30, "min_oi": 50, "beta": 1.4,
    },
    "KRE": {
        "call": "Regional banks recover on Fed cut + oil drop",
        "put": "Oil recession = loan defaults = bank crisis 2.0",
        "catalyst": "Fed decision, oil reversal, bank earnings",
        "max_otm": 18, "min_vol": 10, "min_oi": 30, "beta": 1.3,
    },
    "GDX": {
        "call": "Gold miners surge on rate cuts + dollar weakness",
        "put": "Dollar strength = gold drops = miners crushed",
        "catalyst": "Fed pivot, dollar index, gold price",
        "max_otm": 15, "min_vol": 10, "min_oi": 20, "beta": 1.5,
    },
    "IBIT": {
        "call": "BTC depressed by war. Peace = risk-on = BTC $85K+",
        "put": "Crypto winter extends on macro fear",
        "catalyst": "Ceasefire, ETF flows, Fed signals",
        "max_otm": 20, "min_vol": 20, "min_oi": 30, "beta": 1.8,
    },
    "SMH": {
        "call": "Semis oversold. AI capex intact. Mean reversion 15%",
        "put": "Trade war + chip bans = semis drop another 15%",
        "catalyst": "NVDA/AMD earnings, trade deals, AI capex",
        "max_otm": 12, "min_vol": 50, "min_oi": 100, "beta": 1.3,
    },
    "XLF": {
        "call": "Financials pop on rate cut clarity",
        "put": "Recession = loan losses = financials dump",
        "catalyst": "FOMC, yield curve, bank earnings",
        "max_otm": 12, "min_vol": 20, "min_oi": 30, "beta": 1.1,
    },
    "SPY": {
        "call": "War ends = market rips on relief rally",
        "put": "Oil recession + Fed stuck = market -10-15%",
        "catalyst": "Ceasefire, FOMC, GDP, earnings season",
        "max_otm": 8, "min_vol": 100, "min_oi": 200, "beta": 1.0,
    },
    "XOP": {
        "call": "Oil E&P pure play. Higher beta than XLE",
        "put": "Peace = oil crash = XOP -25% (high beta both ways)",
        "catalyst": "Same as XLE amplified",
        "max_otm": 15, "min_vol": 20, "min_oi": 30, "beta": 1.6,
    },
    "ITA": {
        "call": "Defense spending up regardless. Election cycle boost",
        "put": "Peace = defense budget cut narrative",
        "catalyst": "Defense budget, contracts, election",
        "max_otm": 12, "min_vol": 10, "min_oi": 20, "beta": 0.9,
    },
}

# Keyword-to-trade mapping for news headline scanning.
# Each keyword maps to a suggested play and the reasoning behind it.
TRADE_MAP: dict[str, tuple[str, str]] = {
    "ceasefire": ("JETS calls / XLE puts", "Peace = oil down airlines up"),
    "peace talk": ("JETS calls / XLE puts", "De-escalation signal"),
    "peace deal": ("JETS calls / TLT calls", "Major de-escalation"),
    "iran deal": ("JETS calls / TLT calls", "De-escalation"),
    "hormuz": ("XLE calls / XOP calls", "Supply choke = oil up"),
    "tariff": ("SMH puts / SPY puts", "Trade war = risk off"),
    "sanctions": ("XLE calls", "Supply squeeze"),
    "rate cut": ("TLT calls / KRE calls", "Dovish = bonds+banks"),
    "military": ("ITA calls / XLE calls", "Escalation"),
    "destroy": ("XLE calls / ITA calls", "Extreme escalation"),
    "kharg": ("XLE calls", "Direct oil supply threat"),
    "oil well": ("XLE calls / XOP calls", "Supply destruction"),
    "ground offensive": ("XLE calls / ITA calls", "Major escalation"),
    "nuclear": ("GDX calls / TLT calls", "Flight to safety"),
}

# Keywords that identify relevant news sources
NEWS_KEYWORDS: list[str] = [
    "trump", "truth social", "president said", "white house",
]
