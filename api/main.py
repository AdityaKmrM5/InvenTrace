"""
InvenTrace API — a thin FastAPI layer over the `inventrace` package."""


import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks

from inventrace import (
    DEFAULT_LEAD_TIMES,
    load_all,
    melt_to_long,
    compute_demand_stats,
    compute_price_stats,
    add_cost_params,
    add_safety_stock_and_reorder_point,
    patch_stockpyl,
    get_optimal_policy,
    get_naive_policy,
    batch_evaluate,
)
from inventrace.data import resolve_data_dir

from api.schemas import (
    PolicyResponse,
    TopSkusResponse,
    SkuVolume,
    BatchRunRequest,
    BatchRunResponse,
    BatchStatusResponse,
    BatchResultRow,
)

state = {}

jobs: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):

#Load data and compute echelon stats once when the API starts up.

    data_dir = resolve_data_dir()
    print(f"[startup] Loading data from {data_dir}")

    calendar_df, sales_df, prices_df = load_all(data_dir)
    melted = melt_to_long(sales_df, calendar_df, sample_size=1000)
    echelon1_stats, echelon2_stats, echelon3_stats = compute_demand_stats(melted)

    price_stats = compute_price_stats(prices_df)
    echelon1_stats, echelon2_stats, echelon3_stats = add_cost_params(
        echelon1_stats, echelon2_stats, echelon3_stats, price_stats
    )

    echelon3_stats = add_safety_stock_and_reorder_point(
        echelon3_stats, DEFAULT_LEAD_TIMES.echelon3_store, "h_echelon3", clip_negative=False
    )
    echelon2_stats = add_safety_stock_and_reorder_point(
        echelon2_stats, DEFAULT_LEAD_TIMES.echelon2_state, "h_echelon2", clip_negative=True
    )
    echelon1_stats = add_safety_stock_and_reorder_point(
        echelon1_stats, DEFAULT_LEAD_TIMES.echelon1_national, "h_echelon1", clip_negative=True
    )

    patch_stockpyl()

    state["echelon1_stats"] = echelon1_stats
    state["echelon2_stats"] = echelon2_stats
    state["echelon3_stats"] = echelon3_stats
    state["melted"] = melted

    print("[startup] Ready.")
    yield
    state.clear()


app = FastAPI(
    title="InvenTrace API",
    description="Multi-echelon inventory optimization — optimal vs. naive policy per SKU/store.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok", "data_loaded": "echelon3_stats" in state}


@app.get("/policy/{store}/{sku}", response_model=PolicyResponse)
def get_policy(store: str, sku: str):

    echelon1_stats = state["echelon1_stats"]
    echelon2_stats = state["echelon2_stats"]
    echelon3_stats = state["echelon3_stats"]

    try:
        optimal = get_optimal_policy(sku, store, echelon1_stats, echelon2_stats, echelon3_stats)
    except (IndexError, KeyError):
        raise HTTPException(status_code=404, detail=f"No data found for SKU '{sku}' at store '{store}'")

    naive = get_naive_policy(
        optimal["network"],
        optimal["rows"]["echelon1"],
        optimal["rows"]["echelon2"],
        optimal["rows"]["echelon3"],
    )

    C_star = optimal["C_star"]
    C_naive = naive["C_naive"]
    improvement_pct = (C_naive - C_star) / C_naive * 100 if C_naive > 0 else None

    return PolicyResponse(
        sku=sku,
        store=store,
        optimized_base_stock={
            "echelon3": optimal["S_star"][3],
            "echelon2": optimal["S_star"][2],
            "echelon1": optimal["S_star"][1],
        },
        optimized_expected_cost=C_star,
        naive_expected_cost=C_naive,
        cost_reduction_pct=improvement_pct,
    )


@app.get("/skus/top", response_model=TopSkusResponse)
def get_top_skus(n: int = 20):

    melted = state["melted"]
    top = (
        melted.groupby(["store_id", "item_id"])["sales"]
        .sum()
        .reset_index(name="total_units_sold")
        .sort_values("total_units_sold", ascending=False)
        .head(n)
    )
    skus = [SkuVolume(**row) for row in top.to_dict(orient="records")]
    return TopSkusResponse(count=len(skus), skus=skus)


def _run_batch_job(job_id: str, n_skus: int):

    try:
        echelon1_stats = state["echelon1_stats"]
        echelon2_stats = state["echelon2_stats"]
        echelon3_stats = state["echelon3_stats"]

        combos = echelon3_stats[["store_id", "item_id"]].drop_duplicates().head(n_skus)
        results_df = batch_evaluate(combos, echelon1_stats, echelon2_stats, echelon3_stats)

        jobs[job_id] = {
            "status": "done",
            "results": [BatchResultRow(**row) for row in results_df.to_dict(orient="records")],
        }
    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}


@app.post("/run-batch", response_model=BatchRunResponse)
def run_batch(request: BatchRunRequest, background_tasks: BackgroundTasks):

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running"}
    background_tasks.add_task(_run_batch_job, job_id, request.n_skus)
    return BatchRunResponse(job_id=job_id, status="running")


@app.get("/run-batch/{job_id}", response_model=BatchStatusResponse)
def get_batch_status(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return BatchStatusResponse(job_id=job_id, **job)