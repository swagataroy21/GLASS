from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import polars as pl
import pandas as pd
from datetime import datetime
import os
import shutil

app = FastAPI()

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_files"
PARQUET_FILE = os.path.join(UPLOAD_DIR, "input_data.parquet")
MAPPING_FILE = "./mapping/division_mapping.xlsx"  # Local Excel with Division ↔ Business Area

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Helper: Load division mapping Excel
def load_division_mapping() -> pd.DataFrame:
    if os.path.exists(MAPPING_FILE):
        return pd.read_excel(MAPPING_FILE)
    else:
        raise FileNotFoundError("Division mapping file not found.")

# Helper: Derive columns
def derive_columns(df: pl.DataFrame, current_date: datetime) -> pl.DataFrame:
    # Parse Posting Date
    df = df.with_columns([
        pl.col("BUDAT").str.strptime(pl.Date, format="%d-%m-%Y", strict=False).alias("PostingDate"),
    ])

    # Ageing bucket
    df = df.with_columns([
        (current_date - pl.col("PostingDate")).dt.days().alias("DaysOld")
    ])

    df = df.with_columns([
        pl.when(pl.col("DaysOld") < 183).then("<6 Months")
          .when(pl.col("DaysOld") < 365).then("6M-1Y")
          .when(pl.col("DaysOld") < 730).then("1-2Y")
          .when(pl.col("DaysOld") < 1095).then("2-3Y")
          .when(pl.col("DaysOld") < 1825).then("3-5Y")
          .otherwise(">5Y")
          .alias("Ageing")
    ])

    # Division mapping
    try:
        mapping_df = load_division_mapping()
        pl_map = pl.from_pandas(mapping_df)
        df = df.join(pl_map, left_on="RBUSA", right_on="Business Area", how="left")
        df = df.with_columns([
            pl.col("Division").fill_null("Others")
        ])
    except Exception as e:
        df = df.with_columns([pl.lit("Others").alias("Division")])

    return df

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        temp_csv_path = os.path.join(UPLOAD_DIR, file.filename)

        # Save to disk
        with open(temp_csv_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Read + convert to Parquet
        df = pl.read_csv(temp_csv_path, separator=";")
        df.write_parquet(PARQUET_FILE)

        return {"status": "success", "message": "File uploaded and converted to Parquet."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/gl-accounts")
def get_gl_accounts():
    try:
        df = pl.read_parquet(PARQUET_FILE)
        return {"gl_accounts": df.select("RACCT").unique().to_series().to_list()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/load-default")
def load_default_file():
    try:
        if not os.path.exists(PARQUET_FILE):
            return JSONResponse(status_code=404, content={"status": "error", "message": "No file uploaded yet."})

        df = pl.read_parquet(PARQUET_FILE)
        return {"columns": df.columns, "rows": df.head(5).to_dicts()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/drilldown1")
async def drilldown_level_1(gl_account: str = Form(...), current_date: str = Form(...)):
    try:
        df = pl.read_parquet(PARQUET_FILE)
        df = df.filter(pl.col("RACCT") == gl_account)

        # Convert string date to datetime
        current_dt = datetime.strptime(current_date, "%Y-%m-%d")

        df = derive_columns(df, current_dt)

        # Group by RACCT and Ageing
        ageing_table = df.groupby(["RACCT", "Ageing"]).agg([
            pl.col("HSL").sum().alias("Amount")
        ]).sort("Ageing")

        # Group by RACCT and Division
        division_table = df.groupby(["RACCT", "Division"]).agg([
            pl.col("HSL").sum().alias("Amount")
        ]).sort("Division")

        return {
            "ageing_table": ageing_table.to_dicts(),
            "division_table": division_table.to_dicts(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
