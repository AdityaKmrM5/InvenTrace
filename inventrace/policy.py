#Newsvendor-style safety stock and reorder point calculations

import numpy as np
import pandas as pd
from scipy.stats import norm


def add_safety_stock_and_reorder_point(
    stats_df: pd.DataFrame,
    lead_time_days: float,
    holding_cost_col: str,
    clip_negative: bool = True,
) -> pd.DataFrame:

    df = stats_df.copy()
    df['critical_ratio'] = df['penalty_cost'] / (df['penalty_cost'] + df[holding_cost_col])
    df['z_score'] = norm.ppf(df['critical_ratio'])

    safety_stock = df['z_score'] * df['sigma_demand'] * np.sqrt(lead_time_days)
    df['safety_stock'] = safety_stock.clip(lower=0) if clip_negative else safety_stock

    df['reorder_point'] = (df['mu_demand'] * lead_time_days) + df['safety_stock']
    return df
