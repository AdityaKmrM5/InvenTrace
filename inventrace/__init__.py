"""
InvenTrace — Multi-Echelon Inventory Optimization

A small, reusable package that turns the InvenTrace notebook's logic into
plain functions: load data, build the 3-echelon hierarchy, compute demand
and cost statistics, derive safety stock / reorder points, and solve for
optimal multi-echelon base-stock levels vs. a naive policy.
"""

from .config import LeadTimes, DEFAULT_LEAD_TIMES
from .data import load_all
from .echelons import melt_to_long, compute_demand_stats
from .costs import (
    compute_price_stats,
    add_cost_params,
    add_cost_params_echelon1,
    add_cost_params_echelon2,
    add_cost_params_echelon3,
)
from .policy import add_safety_stock_and_reorder_point
from .optimize import (
    patch_stockpyl,
    get_optimal_policy,
    get_naive_policy,
    evaluate_combo,
    batch_evaluate,
)

__all__ = [
    "LeadTimes",
    "DEFAULT_LEAD_TIMES",
    "load_all",
    "melt_to_long",
    "compute_demand_stats",
    "compute_price_stats",
    "add_cost_params",
    "add_cost_params_echelon1",
    "add_cost_params_echelon2",
    "add_cost_params_echelon3",
    "add_safety_stock_and_reorder_point",
    "patch_stockpyl",
    "get_optimal_policy",
    "get_naive_policy",
    "evaluate_combo",
    "batch_evaluate",
]

__version__ = "0.1.0"
