from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import polars as pl
import pandas as pd
import os
import shutil
from datetime import datetime

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

os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        temp_csv_path = os.path.join(UPLOAD_DIR, file.filename)

        # Save CSV to temp path
        with open(temp_csv_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Convert to Parquet
        df = pl.read_csv(temp_csv_path, separator=";")  # ABAP CSVs use semicolon
        df.write_parquet(PARQUET_FILE)

        return {"status": "success", "message": "File uploaded and converted to Parquet."}

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/gl-accounts")
def get_gl_accounts():
    try:
        df = pl.read_parquet(PARQUET_FILE)
        gl_accounts = df.select("G/L Account").unique().to_series().to_list()
        return {"gl_accounts": gl_accounts}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/load-default")
def load_default_file():
    try:
        # TODO: GCP support - load from GCS or BigQuery if available
        if not os.path.exists(PARQUET_FILE):
            return JSONResponse(status_code=404, content={"status": "error", "message": "No file uploaded yet."})

        df = pl.read_parquet(PARQUET_FILE)
        return {"columns": df.columns, "rows": df.head(5).to_dicts()}

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
