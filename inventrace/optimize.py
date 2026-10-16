"""
Multi-echelon base-stock optimization via stockpyl, plus a naive
(independently-set reorder point) policy for comparison.
"""

import time
from typing import Dict, List, Optional

import pandas as pd

from .config import LeadTimes, DEFAULT_LEAD_TIMES


def patch_stockpyl() -> None:
    """
    stockpyl calls np.array(..., copy=False), an argument removed in
    NumPy 2.0. This patches the installed stockpyl source in place to
    strip that argument, so it works regardless of NumPy version.

    Implemented in pure Python (not shell find/sed) so it works on
    Windows, macOS, and Linux alike. Safe to call multiple times
    (no-op if already patched).
    """
    import stockpyl
    import os

    pkg_dir = os.path.dirname(stockpyl.__file__)

    for root, _dirs, files in os.walk(pkg_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, OSError):
                continue

            if ", copy=False" not in content:
                continue

            patched = content.replace(", copy=False", "")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(patched)


def _get_rows(sku: str, store: str, echelon1_stats, echelon2_stats, echelon3_stats):
    state = store.split('_')[0]
    row3 = echelon3_stats[(echelon3_stats.store_id == store) & (echelon3_stats.item_id == sku)].iloc[0]
    row2 = echelon2_stats[(echelon2_stats.state_id == state) & (echelon2_stats.item_id == sku)].iloc[0]
    row1 = echelon1_stats[echelon1_stats.item_id == sku].iloc[0]
    return row1, row2, row3


def _build_network(row1, row2, row3, lead_times: LeadTimes):
    from stockpyl.supply_chain_network import serial_system

    return serial_system(
        num_nodes=3,
        node_order_in_system=[3, 2, 1],
        echelon_holding_cost=[row3['h_echelon3'], row2['h_echelon2'], row1['h_echelon1']],
        shipment_lead_time=[
            lead_times.echelon3_store,
            lead_times.echelon2_state,
            lead_times.echelon1_national,
        ],
        stockout_cost=row3['penalty_cost'],
        demand_type='N',
        mean=row3['mu_demand'],
        standard_deviation=row3['sigma_demand'],
    )


def get_optimal_policy(
    sku: str,
    store: str,
    echelon1_stats: pd.DataFrame,
    echelon2_stats: pd.DataFrame,
    echelon3_stats: pd.DataFrame,
    lead_times: LeadTimes = DEFAULT_LEAD_TIMES,
) -> Dict:
    """
    Solve for the optimal echelon base-stock levels for one SKU/store,
    using stockpyl's serial-system solver.

    Returns {'network': ..., 'S_star': {...}, 'C_star': float}.
    """
    from stockpyl.ssm_serial import optimize_base_stock_levels

    row1, row2, row3 = _get_rows(sku, store, echelon1_stats, echelon2_stats, echelon3_stats)
    network = _build_network(row1, row2, row3, lead_times)
    S_star, C_star = optimize_base_stock_levels(network=network)
    return {"network": network, "S_star": S_star, "C_star": C_star,
            "rows": {"echelon1": row1, "echelon2": row2, "echelon3": row3}}


def get_naive_policy(network, row1, row2, row3) -> Dict:
    """
    Convert each echelon's independently-computed reorder point into an
    echelon base-stock level and evaluate its expected cost, for
    comparison against the jointly-optimized policy.
    """
    from stockpyl.supply_chain_network import local_to_echelon_base_stock_levels
    from stockpyl.ssm_serial import expected_cost

    S_naive_local = {
        3: row3['reorder_point'],
        2: row2['reorder_point'],
        1: row1['reorder_point'],
    }
    S_naive_echelon = local_to_echelon_base_stock_levels(network, S_naive_local)
    C_naive = expected_cost(S_naive_echelon, network=network, x_num=100, d_num=10)
    return {"S_naive_local": S_naive_local, "S_naive_echelon": S_naive_echelon, "C_naive": C_naive}


def evaluate_combo(
    store: str,
    sku: str,
    echelon1_stats: pd.DataFrame,
    echelon2_stats: pd.DataFrame,
    echelon3_stats: pd.DataFrame,
    lead_times: LeadTimes = DEFAULT_LEAD_TIMES,
) -> Optional[Dict]:
    """
    Run both the optimal and naive policy for one SKU/store and return
    a single result dict with the cost comparison. Returns None if the
    SKU/store has no demand variance (nothing to optimize).
    """
    row1, row2, row3 = _get_rows(sku, store, echelon1_stats, echelon2_stats, echelon3_stats)
    if row3['sigma_demand'] <= 0:
        return None

    network = _build_network(row1, row2, row3, lead_times)

    from stockpyl.ssm_serial import optimize_base_stock_levels
    S_star, C_star = optimize_base_stock_levels(network=network)

    naive = get_naive_policy(network, row1, row2, row3)
    C_naive = naive["C_naive"]
    improvement_pct = (C_naive - C_star) / C_naive * 100 if C_naive > 0 else None

    return {
        "store_id": store,
        "item_id": sku,
        "S3_optimized": S_star[3],
        "S2_optimized": S_star[2],
        "S1_optimized": S_star[1],
        "C_optimized": C_star,
        "C_naive": C_naive,
        "improvement_pct": improvement_pct,
    }


def batch_evaluate(
    combos: pd.DataFrame,
    echelon1_stats: pd.DataFrame,
    echelon2_stats: pd.DataFrame,
    echelon3_stats: pd.DataFrame,
    lead_times: LeadTimes = DEFAULT_LEAD_TIMES,
    progress_every: int = 20,
) -> pd.DataFrame:
    """
    Run evaluate_combo() over a dataframe of {store_id, item_id} combos
    and return the results as a dataframe. SKU/store combos that error
    out or have zero demand variance are skipped, not raised.
    """
    results: List[Dict] = []
    start_time = time.time()

    for i, (_, combo) in enumerate(combos.iterrows()):
        try:
            result = evaluate_combo(
                combo['store_id'], combo['item_id'],
                echelon1_stats, echelon2_stats, echelon3_stats, lead_times,
            )
            if result is not None:
                results.append(result)
        except Exception as e:
            print(f"Skipped {combo['item_id']} @ {combo['store_id']}: {e}")

        if progress_every and (i + 1) % progress_every == 0:
            elapsed = time.time() - start_time
            print(f"Processed {i + 1}/{len(combos)} — {elapsed / 60:.1f} min elapsed")

    return pd.DataFrame(results)
