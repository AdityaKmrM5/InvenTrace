#Build the Store -> State -> National echelon hierarchy and demand stats

from typing import Tuple

import pandas as pd

ID_COLS = ['id', 'item_id', 'dept_id', 'cat_id', 'store_id', 'state_id']


def melt_to_long(
    sales_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
    sample_size: int = 1000,
    random_state: int = 42,
) -> pd.DataFrame:

    if sample_size is not None and len(sales_df) > sample_size:
        sales_sample = sales_df.sample(n=sample_size, random_state=random_state)
    else:
        sales_sample = sales_df

    d_cols = [c for c in sales_sample.columns if c.startswith('d_')]

    melted = pd.melt(
        sales_sample,
        id_vars=ID_COLS,
        value_vars=d_cols,
        var_name='d',
        value_name='sales',
    )
    melted = melted.merge(calendar_df[['d', 'date', 'wm_yr_wk']], on='d', how='left')
    melted['date'] = pd.to_datetime(melted['date'])
    return melted


def compute_demand_stats(melted: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    echelon3_stats = (
        melted.groupby(['store_id', 'item_id'])['sales']
        .agg(mu_demand='mean', sigma_demand='std')
        .reset_index()
    )
    echelon2_stats = (
        melted.groupby(['state_id', 'item_id'])['sales']
        .agg(mu_demand='mean', sigma_demand='std')
        .reset_index()
    )
    echelon1_stats = (
        melted.groupby('item_id')['sales']
        .agg(mu_demand='mean', sigma_demand='std')
        .reset_index()
    )
    return echelon1_stats, echelon2_stats, echelon3_stats
