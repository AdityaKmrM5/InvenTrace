"""Shared configuration: lead times and cost-model multipliers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LeadTimes:
    """Shipment lead time (in days) at each echelon."""
    echelon1_national: int = 21   # Central DC — longest lead time
    echelon2_state: int = 14      # Regional DC
    echelon3_store: int = 7       # Store — shortest lead time


DEFAULT_LEAD_TIMES = LeadTimes()

HOLDING_COST_ANNUAL_RATE = 0.20     # 20% of unit price per year
STOCKOUT_PENALTY_MULTIPLE = 5.0     # penalty_cost = holding_cost * multiple
DEFAULT_UNIT_PRICE_FALLBACK = 2.50  # used when an item has no price data

ECHELON3_HOLDING_COST_SCALE = 1.0
ECHELON2_HOLDING_COST_SCALE = 1.2
ECHELON1_HOLDING_COST_SCALE = 1.0
