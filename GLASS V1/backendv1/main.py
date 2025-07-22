# main.py (Phase 1 - Backend Upload + Preprocessing + Two Tables)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import shutil
import os
import polars as pl
import pandas as pd
from datetime import datetime

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_files"
DEFAULT_CSV_PATH = "./data/default_file.csv"
DEFAULT_MAPPING_PATH = "./data/division_mapping.xlsx"
PARQUET_PATH = "./uploaded_files/data.parquet"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Columns of interest
AMOUNT_COL = "HSL"
GL_ACCOUNT_COL = "RACCT"
POSTING_DATE_COL = "BUDAT"
BUSINESS_AREA_COL = "RBUSA"

AGE_BUCKETS = [
    (0, 180, "<6 months"),
    (181, 365, "6M-1Y"),
    (366, 730, "1-2Y"),
    (731, 1095, "2-3Y"),
    (1096, 1825, "3-5Y"),
    (1826, 100000, ">5Y"),
]

def load_and_prepare_data(file_path: str, mapping_path: str, ref_date: datetime) -> pl.DataFrame:
    df = pl.read_csv(file_path, separator=";")

    # Clean date
    df = df.with_columns(
        pl.col(POSTING_DATE_COL).str.strptime(pl.Date, format="%d-%m-%Y", strict=False).alias("_post_date")
    )

    # Calculate ageing bucket
    df = df.with_columns(
        (ref_date - pl.col("_post_date")).dt.days().alias("_age_days")
    )
    for lower, upper, label in AGE_BUCKETS:
        df = df.with_columns(
            pl.when((pl.col("_age_days") >= lower) & (pl.col("_age_days") <= upper))
            .then(label)
            .otherwise(pl.col("Ageing") if "Ageing" in df.columns else "")
            .alias("Ageing")
        )

    # Load mapping and join for Division
    map_df = pd.read_excel(mapping_path)
    map_pl = pl.from_pandas(map_df)
    df = df.join(map_pl, left_on=BUSINESS_AREA_COL, right_on="Business Area", how="left")
    df = df.with_columns(
        pl.col("Division").fill_null("Others")
    )

    return df

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Convert CSV to Parquet
        df = pl.read_csv(file_path, separator=";")
        df.write_parquet(PARQUET_PATH)

        return {"status": "success", "message": "File uploaded and converted to Parquet."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/initial-gl-options")
def get_gl_account_options():
    if not os.path.exists(PARQUET_PATH):
        df = pl.read_csv(DEFAULT_CSV_PATH, separator=";")
        df.write_parquet(PARQUET_PATH)
    else:
        df = pl.read_parquet(PARQUET_PATH)

    return {"gl_accounts": df.select(GL_ACCOUNT_COL).unique().to_series().to_list()}

@app.get("/initial-summary")
def get_initial_summary(gl_account: str, reference_date: str = None):
    if not os.path.exists(PARQUET_PATH):
        raise HTTPException(status_code=400, detail="No data file available.")

    ref_date = datetime.strptime(reference_date, "%Y-%m-%d") if reference_date else datetime.today()
    df = load_and_prepare_data(PARQUET_PATH, DEFAULT_MAPPING_PATH, ref_date)

    filtered_df = df.filter(pl.col(GL_ACCOUNT_COL) == gl_account)

    ageing_group = (
        filtered_df
        .group_by("Ageing")
        .agg(pl.col(AMOUNT_COL).sum().alias("Amount"))
        .sort("Ageing")
    )

    division_group = (
        filtered_df
        .group_by("Division")
        .agg(pl.col(AMOUNT_COL).sum().alias("Amount"))
        .sort("Division")
    )

    return JSONResponse({
        "ageing_table": ageing_group.to_dicts(),
        "division_table": division_group.to_dicts()
    })

