"""Loading the M5 dataset files (calendar, sales, prices)."""

import os
from typing import Tuple

import pandas as pd


def resolve_data_dir() -> str:

    try:
        from google.colab import drive  # type: ignore
        drive.mount('/content/drive')
        return '/content/drive/MyDrive/MEIO'
    except ImportError:
        return os.environ.get('MEIO_DATA_DIR', './data')


def load_calendar(data_dir: str) -> pd.DataFrame:
    return pd.read_csv(f'{data_dir}/calendar.csv')


def load_sales(data_dir: str) -> pd.DataFrame:
    return pd.read_csv(f'{data_dir}/sales_train_validation.csv')


def load_prices(data_dir: str) -> pd.DataFrame:
    return pd.read_csv(f'{data_dir}/sell_prices.csv')


def load_all(data_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load calendar, sales, and prices in one call."""
    calendar_df = load_calendar(data_dir)
    sales_df = load_sales(data_dir)
    prices_df = load_prices(data_dir)
    return calendar_df, sales_df, prices_df
