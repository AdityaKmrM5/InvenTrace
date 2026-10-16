"""Per-echelon holding-cost and stockout-penalty parameters."""

import pandas as pd

from .config import (
    HOLDING_COST_ANNUAL_RATE,
    STOCKOUT_PENALTY_MULTIPLE,
    DEFAULT_UNIT_PRICE_FALLBACK,
    ECHELON1_HOLDING_COST_SCALE,
    ECHELON2_HOLDING_COST_SCALE,
    ECHELON3_HOLDING_COST_SCALE,
)


def compute_price_stats(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Average sell price per item across all store/week records."""
    return prices_df.groupby('item_id')['sell_price'].mean().reset_index()


def _add_holding_and_penalty(
    stats_df: pd.DataFrame,
    price_stats: pd.DataFrame,
    holding_col: str,
    scale: float,
) -> pd.DataFrame:
    df = stats_df.merge(price_stats, on='item_id', how='left').fillna(
        {'sell_price': DEFAULT_UNIT_PRICE_FALLBACK}
    )
    df[holding_col] = (df['sell_price'] * HOLDING_COST_ANNUAL_RATE / 365.0) * scale
    df['penalty_cost'] = df[holding_col] * STOCKOUT_PENALTY_MULTIPLE
    df['sigma_demand'] = df['sigma_demand'].fillna(0)
    return df


def add_cost_params_echelon3(echelon3_stats: pd.DataFrame, price_stats: pd.DataFrame) -> pd.DataFrame:
    """Add sell_price, h_echelon3, and penalty_cost to store-level stats."""
    return _add_holding_and_penalty(
        echelon3_stats, price_stats, 'h_echelon3', ECHELON3_HOLDING_COST_SCALE
    )


def add_cost_params_echelon2(echelon2_stats: pd.DataFrame, price_stats: pd.DataFrame) -> pd.DataFrame:
    """Add sell_price, h_echelon2, and penalty_cost to state-level stats."""
    return _add_holding_and_penalty(
        echelon2_stats, price_stats, 'h_echelon2', ECHELON2_HOLDING_COST_SCALE
    )


def add_cost_params_echelon1(echelon1_stats: pd.DataFrame, price_stats: pd.DataFrame) -> pd.DataFrame:
    """Add sell_price, h_echelon1, and penalty_cost to national-level stats."""
    return _add_holding_and_penalty(
        echelon1_stats, price_stats, 'h_echelon1', ECHELON1_HOLDING_COST_SCALE
    )


def add_cost_params(
    echelon1_stats: pd.DataFrame,
    echelon2_stats: pd.DataFrame,
    echelon3_stats: pd.DataFrame,
    price_stats: pd.DataFrame,
):
    """Convenience wrapper: add cost params to all three echelons at once."""
    echelon3_stats = add_cost_params_echelon3(echelon3_stats, price_stats)
    echelon2_stats = add_cost_params_echelon2(echelon2_stats, price_stats)
    echelon1_stats = add_cost_params_echelon1(echelon1_stats, price_stats)
    return echelon1_stats, echelon2_stats, echelon3_stats
