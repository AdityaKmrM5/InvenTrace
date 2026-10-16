"""Pydantic models describing the API's request/response shapes."""

from typing import Optional, List
from pydantic import BaseModel


class PolicyResponse(BaseModel):
    sku: str
    store: str
    optimized_base_stock: dict          # {"echelon3": .., "echelon2": .., "echelon1": ..}
    optimized_expected_cost: float
    naive_expected_cost: float
    cost_reduction_pct: Optional[float]


class SkuVolume(BaseModel):
    store_id: str
    item_id: str
    total_units_sold: float


class TopSkusResponse(BaseModel):
    count: int
    skus: List[SkuVolume]


class BatchRunRequest(BaseModel):
    n_skus: int = 20


class BatchRunResponse(BaseModel):
    job_id: str
    status: str


class BatchResultRow(BaseModel):
    store_id: str
    item_id: str
    C_optimized: float
    C_naive: float
    improvement_pct: Optional[float]


class BatchStatusResponse(BaseModel):
    job_id: str
    status: str                          # "running" | "done" | "failed"
    results: Optional[List[BatchResultRow]] = None
    error: Optional[str] = None
