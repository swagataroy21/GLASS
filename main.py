from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import polars as pl
import pandas as pd
import os
import shutil
from datetime import datetime

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_files"
PARQUET_FILE = os.path.join(UPLOAD_DIR, "input_data.parquet")
MAPPING_FILE = "./mapping_files/division_mapping.xlsx"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Utility: Load mapping Excel
def load_mapping():
    if os.path.exists(MAPPING_FILE):
        df = pd.read_excel(MAPPING_FILE)
        return dict(zip(df['Business Area'], df['Division']))
    return {}

# Utility: Derive ageing & division columns
def derive_columns(df: pl.DataFrame, reference_date: datetime):
    mapping_dict = load_mapping()
    df = df.with_columns([
        pl.col("Posting Date").str.strptime(pl.Date, "%Y-%m-%d", strict=False).alias("Posting_Date_Parsed")
    ])

    # Ageing
    df = df.with_columns([
        (pl.lit(reference_date) - pl.col("Posting_Date_Parsed")).dt.days().alias("Age_Days")
    ])

    def ageing_bucket(days):
        if days < 180: return "<6 months"
        elif days < 365: return "6m–1y"
        elif days < 730: return "1–2y"
        elif days < 1095: return "2–3y"
        elif days < 1825: return "3–5y"
        else: return ">5y"

    df = df.with_columns([
        pl.col("Age_Days").apply(ageing_bucket).alias("Ageing")
    ])

    # Division
    df = df.with_columns([
        pl.col("Business Area").apply(lambda x: mapping_dict.get(x, "Others")).alias("Division")
    ])

    return df

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        temp_csv_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(temp_csv_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        df = pl.read_csv(temp_csv_path, separator=";")
        df.write_parquet(PARQUET_FILE)
        return {"status": "success", "message": "File uploaded and converted to Parquet."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/gl-accounts")
def get_gl_accounts():
    try:
        df = pl.read_parquet(PARQUET_FILE)
        return {"gl_accounts": df.select("G/L Account").unique().to_series().to_list()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/filtered-summary")
def get_filtered_summary(gl_account: str, reference_date: str = Query(default=None)):
    try:
        df = pl.read_parquet(PARQUET_FILE)
        ref_date = datetime.strptime(reference_date, "%Y-%m-%d") if reference_date else datetime.today()
        df = df.filter(pl.col("G/L Account") == gl_account)
        df = derive_columns(df, ref_date)

        ageing_summary = df.groupby("Ageing").agg(pl.col("Amount in Local Currency").sum()).sort("Ageing")
        division_summary = df.groupby("Division").agg(pl.col("Amount in Local Currency").sum()).sort("Division")

        return {
            "ageing_summary": {
                "columns": ageing_summary.columns,
                "rows": ageing_summary.to_dicts()
            },
            "division_summary": {
                "columns": division_summary.columns,
                "rows": division_summary.to_dicts()
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/drilldown1")
def drilldown_1(gl_account: str, ageing: str, division: str, reference_date: str = Query(default=None)):
    try:
        df = pl.read_parquet(PARQUET_FILE)
        ref_date = datetime.strptime(reference_date, "%Y-%m-%d") if reference_date else datetime.today()
        df = df.filter(pl.col("G/L Account") == gl_account)
        df = derive_columns(df, ref_date)

        df = df.filter((pl.col("Ageing") == ageing) & (pl.col("Division") == division))

        grouped = df.groupby(["Ageing", "Division"]).agg(
            pl.col("Amount in Local Currency").sum()
        )

        return {
            "columns": grouped.columns,
            "rows": grouped.to_dicts()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
