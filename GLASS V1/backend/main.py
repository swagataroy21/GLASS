from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import polars as pl
import os
import shutil
from datetime import datetime

app = FastAPI()

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploaded_files"
PARQUET_FILE = os.path.join(UPLOAD_DIR, "input_data.parquet")
MAPPING_FILE = os.path.join(UPLOAD_DIR, "mapping_file.xlsx")  # or .csv

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ========== Helper: Add derived columns ==========
def derive_columns(df: pl.DataFrame, current_date: str) -> pl.DataFrame:
    df = df.with_columns([
        pl.col("Posting Date").str.strptime(pl.Date, fmt="%Y-%m-%d", strict=False),
    ])

    current_date_parsed = datetime.strptime(current_date, "%Y-%m-%d")
    df = df.with_columns([
        (pl.lit(current_date_parsed) - pl.col("Posting Date")).dt.days().alias("AgeDays")
    ])

    df = df.with_columns([
        pl.when(pl.col("AgeDays") < 183).then("<6 months")
        .when(pl.col("AgeDays") < 365).then("6 months - 1 year")
        .when(pl.col("AgeDays") < 730).then("1 - 2 years")
        .when(pl.col("AgeDays") < 1095).then("2 - 3 years")
        .when(pl.col("AgeDays") < 1825).then("3 - 5 years")
        .otherwise(">5 years").alias("Ageing")
    ])

    # Map Division from mapping file
    if os.path.exists(MAPPING_FILE):
        try:
            if MAPPING_FILE.endswith(".csv"):
                mapping_df = pl.read_csv(MAPPING_FILE)
            else:
                mapping_df = pl.read_excel(MAPPING_FILE)

            df = df.join(mapping_df, on="Business Area", how="left")
            df = df.with_columns([
                pl.col("Division").fill_null("Others")
            ])
        except Exception as e:
            print(f"[WARN] Failed to load mapping: {e}")
            df = df.with_columns([pl.lit("Others").alias("Division")])
    else:
        df = df.with_columns([pl.lit("Others").alias("Division")])

    return df


# ========== File Upload ==========
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        temp_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        df = pl.read_csv(temp_path, separator=";")
        df.write_parquet(PARQUET_FILE)

        return {"status": "success", "message": "CSV uploaded and converted to Parquet."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/upload-mapping")
async def upload_mapping(file: UploadFile = File(...)):
    try:
        ext = os.path.splitext(file.filename)[-1].lower()
        if ext not in [".xlsx", ".csv"]:
            return JSONResponse(status_code=400, content={"error": "Only .xlsx or .csv allowed"})

        path = MAPPING_FILE
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return {"status": "success", "message": "Mapping file uploaded."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ========== Data Exploration ==========
@app.get("/gl-accounts")
def get_gl_accounts():
    try:
        df = pl.read_parquet(PARQUET_FILE)
        gls = df.select("G/L Account").unique().to_series().to_list()
        return {"gl_accounts": gls}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/load-default")
def load_default_file():
    try:
        if not os.path.exists(PARQUET_FILE):
            return JSONResponse(status_code=404, content={"error": "No file uploaded."})

        df = pl.read_parquet(PARQUET_FILE)
        return {"columns": df.columns, "rows": df.head(5).to_dicts()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ========== Filtered Summary ==========
@app.get("/filtered-summary")
def filtered_summary(gl_account: str = Query(...), current_date: str = Query(None)):
    try:
        df = pl.read_parquet(PARQUET_FILE)
        df = df.filter(pl.col("G/L Account") == gl_account)
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")
        df = derive_columns(df, current_date)

        ageing_group = df.groupby("Ageing").agg(
            pl.col("Amount in Local Currency").sum().alias("Total Amount")
        ).sort("Ageing")

        division_group = df.groupby("Division").agg(
            pl.col("Amount in Local Currency").sum().alias("Total Amount")
        ).sort("Division")

        return {
            "ageing_table": ageing_group.to_dicts(),
            "division_table": division_group.to_dicts()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ========== Drilldown I ==========
@app.get("/drilldown1")
def drilldown_level_1(gl_account: str = Query(...), current_date: str = Query(None)):
    try:
        df = pl.read_parquet(PARQUET_FILE)
        df = df.filter(pl.col("G/L Account") == gl_account)
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")
        df = derive_columns(df, current_date)

        grouped = df.groupby(["Ageing", "Division"]).agg(
            pl.col("Amount in Local Currency").sum().alias("Total Amount")
        ).sort(["Ageing", "Division"])

        return {"columns": grouped.columns, "rows": grouped.to_dicts()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ========== Drilldown II ==========
@app.get("/drilldown2")
def drilldown_level_2(gl_account: str = Query(...), ageing: str = Query(...), division: str = Query(...), current_date: str = Query(None)):
    try:
        df = pl.read_parquet(PARQUET_FILE)
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")
        df = df.filter(pl.col("G/L Account") == gl_account)
        df = derive_columns(df, current_date)

        df = df.filter((pl.col("Ageing") == ageing) & (pl.col("Division") == division))

        grouped = df.groupby("Business Area").agg(
            pl.col("Amount in Local Currency").sum().alias("Total Amount")
        ).sort("Total Amount", descending=True)

        return {"columns": grouped.columns, "rows": grouped.to_dicts()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ========== Drilldown III ==========
@app.get("/drilldown3")
def drilldown_level_3(gl_account: str = Query(...), ageing: str = Query(...), current_date: str = Query(None)):
    try:
        df = pl.read_parquet(PARQUET_FILE)
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")
        df = df.filter(pl.col("G/L Account") == gl_account)
        df = derive_columns(df, current_date)

        df = df.filter(pl.col("Ageing") == ageing)

        grouped = df.groupby(["Division", "Business Area"]).agg(
            pl.col("Amount in Local Currency").sum().alias("Total Amount")
        ).sort(["Division", "Business Area"])

        return {"columns": grouped.columns, "rows": grouped.to_dicts()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ========== Drilldown IV ==========
@app.get("/drilldown4")
def drilldown_level_4(gl_account: str = Query(...), ageing: str = Query(...), division: str = Query(...), business_area: str = Query(...), current_date: str = Query(None)):
    try:
        df = pl.read_parquet(PARQUET_FILE)
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")
        df = df.filter(pl.col("G/L Account") == gl_account)
        df = derive_columns(df, current_date)

        df = df.filter(
            (pl.col("Ageing") == ageing) &
            (pl.col("Division") == division) &
            (pl.col("Business Area") == business_area)
        )

        def blank_to_others(col):
            return pl.when(pl.col(col).is_null() | (pl.col(col).str.strip_chars() == "")).then("Others").otherwise(pl.col(col))

        df = df.with_columns([
            blank_to_others("Vendor Code").alias("Vendor Code"),
            blank_to_others("Vendor Name").alias("Vendor Name"),
            blank_to_others("Customer Code").alias("Customer Code"),
            blank_to_others("Customer Name").alias("Customer Name"),
            blank_to_others("Document Type").alias("Document Type"),
        ])

        vendor_grouped = df.groupby(["Vendor Code", "Vendor Name"]).agg(
            pl.col("Amount in Local Currency").sum().alias("Total Amount")
        ).sort("Total Amount", descending=True)

        customer_grouped = df.groupby(["Customer Code", "Customer Name"]).agg(
            pl.col("Amount in Local Currency").sum().alias("Total Amount")
        ).sort("Total Amount", descending=True)

        doc_type_grouped = df.groupby("Document Type").agg(
            pl.col("Amount in Local Currency").sum().alias("Total Amount")
        ).sort("Total Amount", descending=True)

        return {
            "vendors": vendor_grouped.to_dicts(),
            "customers": customer_grouped.to_dicts(),
            "document_types": doc_type_grouped.to_dicts()
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



# from fastapi import FastAPI, UploadFile, File, Query
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# import polars as pl
# import pandas as pd
# import os
# import shutil
# from datetime import datetime

# app = FastAPI()

# # Allow CORS for local frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# UPLOAD_DIR = "./uploaded_files"
# PARQUET_FILE = os.path.join(UPLOAD_DIR, "input_data.parquet")
# MAPPING_FILE = os.path.join(UPLOAD_DIR, "division_mapping.csv")

# os.makedirs(UPLOAD_DIR, exist_ok=True)

# # --- Upload Endpoints ---

# @app.post("/upload")
# async def upload_file(file: UploadFile = File(...)):
#     try:
#         temp_csv_path = os.path.join(UPLOAD_DIR, file.filename)

#         # Save CSV to temp path
#         with open(temp_csv_path, "wb") as f:
#             shutil.copyfileobj(file.file, f)

#         # Convert to Parquet
#         df = pl.read_csv(temp_csv_path, separator=";")  # ABAP CSVs use semicolon
#         df.write_parquet(PARQUET_FILE)

#         return {"status": "success", "message": "File uploaded and converted to Parquet."}

#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# @app.post("/upload-mapping")
# async def upload_mapping(file: UploadFile = File(...)):
#     try:
#         map_path = os.path.join(UPLOAD_DIR, "division_mapping.csv")
#         with open(map_path, "wb") as f:
#             shutil.copyfileobj(file.file, f)
#         return {"status": "success", "message": "Mapping file uploaded."}
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# # --- Load & Filter Endpoints ---

# @app.get("/gl-accounts")
# def get_gl_accounts():
#     try:
#         df = pl.read_parquet(PARQUET_FILE)
#         gl_accounts = df.select("G/L Account").unique().to_series().to_list()
#         return {"gl_accounts": gl_accounts}
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# @app.get("/load-default")
# def load_default_file():
#     try:
#         # TODO: GCP support - load from GCS or BigQuery if available
#         if not os.path.exists(PARQUET_FILE):
#             return JSONResponse(status_code=404, content={"status": "error", "message": "No file uploaded yet."})

#         df = pl.read_parquet(PARQUET_FILE)
#         return {"columns": df.columns, "rows": df.head(5).to_dicts()}

#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# @app.get("/filtered-summary")
# def filtered_summary(gl_account: str = Query(...), current_date: str = Query(None)):
#     try:
#         df = pl.read_parquet(PARQUET_FILE)

#         if current_date is None:
#             current_date = datetime.now().strftime("%Y-%m-%d")
#         current_dt = datetime.strptime(current_date, "%Y-%m-%d")

#         # Filter by GL Account
#         df = df.filter(pl.col("G/L Account") == gl_account)

#         # Ageing calculation
#         df = df.with_columns([
#             (pl.col("Posting Date").str.strptime(pl.Date, "%Y-%m-%d", strict=False)).alias("posting_dt")
#         ])

#         def classify_age(posting_date):
#             if posting_date is None:
#                 return "Unknown"
#             delta = (current_dt - posting_date).days
#             if delta < 180:
#                 return "<6 months"
#             elif delta < 365:
#                 return "6 months - 1 year"
#             elif delta < 730:
#                 return "1 - 2 years"
#             elif delta < 1095:
#                 return "2 - 3 years"
#             elif delta < 1825:
#                 return "3 - 5 years"
#             else:
#                 return ">5 years"

#         df = df.with_columns([
#             df["posting_dt"].apply(classify_age).alias("Ageing")
#         ])

#         # Merge with mapping file
#         if os.path.exists(MAPPING_FILE):
#             mapping_df = pl.read_csv(MAPPING_FILE)
#             df = df.join(mapping_df, left_on="Business Area", right_on="Business Area", how="left")
#             df = df.with_columns([
#                 pl.when(pl.col("Division").is_null())
#                   .then("Others")
#                   .otherwise(pl.col("Division")).alias("Division")
#             ])
#         else:
#             df = df.with_columns([
#                 pl.lit("Others").alias("Division")
#             ])

#         # Return head for testing
#         return {"columns": df.columns, "rows": df.head(10).to_dicts()}

#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# @app.get("/drilldown1")
# def drilldown_level_1(gl_account: str = Query(...), current_date: str = Query(None)):
#     try:
#         df = pl.read_parquet(PARQUET_FILE)

#         if current_date is None:
#             current_date = datetime.now().strftime("%Y-%m-%d")
#         current_dt = datetime.strptime(current_date, "%Y-%m-%d")

#         # Filter by GL Account
#         df = df.filter(pl.col("G/L Account") == gl_account)

#         # Ageing column
#         df = df.with_columns([
#             (pl.col("Posting Date").str.strptime(pl.Date, "%Y-%m-%d", strict=False)).alias("posting_dt")
#         ])

#         def classify_age(posting_date):
#             if posting_date is None:
#                 return "Unknown"
#             delta = (current_dt - posting_date).days
#             if delta < 180:
#                 return "<6 months"
#             elif delta < 365:
#                 return "6 months - 1 year"
#             elif delta < 730:
#                 return "1 - 2 years"
#             elif delta < 1095:
#                 return "2 - 3 years"
#             elif delta < 1825:
#                 return "3 - 5 years"
#             else:
#                 return ">5 years"

#         df = df.with_columns([
#             df["posting_dt"].apply(classify_age).alias("Ageing")
#         ])

#         # Division mapping
#         if os.path.exists(MAPPING_FILE):
#             mapping_df = pl.read_csv(MAPPING_FILE)
#             df = df.join(mapping_df, left_on="Business Area", right_on="Business Area", how="left")
#             df = df.with_columns([
#                 pl.when(pl.col("Division").is_null())
#                   .then("Others")
#                   .otherwise(pl.col("Division")).alias("Division")
#             ])
#         else:
#             df = df.with_columns([
#                 pl.lit("Others").alias("Division")
#             ])

#         # Group by Ageing + Division
#         grouped = (
#             df.groupby(["Ageing", "Division"])
#               .agg(pl.col("Amount in Local Currency").sum().alias("Total Amount"))
#               .sort(["Ageing", "Division"])
#         )

#         return {
#             "columns": grouped.columns,
#             "rows": grouped.to_dicts()
#         }

#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# # -----------------------------
# # Drilldown II: Division + Ageing → Business Area
# # -----------------------------
# @app.get("/drilldown2")
# def drilldown_level_2(gl_account: str = Query(...), ageing: str = Query(...), division: str = Query(...), current_date: str = Query(None)):
#     try:
#         df = pl.read_parquet(PARQUET_FILE)
#         if current_date is None:
#             current_date = datetime.now().strftime("%Y-%m-%d")

#         df = df.filter(pl.col("G/L Account") == gl_account)
#         df = derive_columns(df, current_date)

#         df = df.filter((pl.col("Ageing") == ageing) & (pl.col("Division") == division))

#         grouped = (
#             df.groupby("Business Area")
#               .agg(pl.col("Amount in Local Currency").sum().alias("Total Amount"))
#               .sort("Total Amount", descending=True)
#         )

#         return {"columns": grouped.columns, "rows": grouped.to_dicts()}
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# # -----------------------------
# # Drilldown III: All Divisions + Ageing + Business Area
# # -----------------------------
# @app.get("/drilldown3")
# def drilldown_level_3(gl_account: str = Query(...), ageing: str = Query(...), current_date: str = Query(None)):
#     try:
#         df = pl.read_parquet(PARQUET_FILE)
#         if current_date is None:
#             current_date = datetime.now().strftime("%Y-%m-%d")

#         df = df.filter(pl.col("G/L Account") == gl_account)
#         df = derive_columns(df, current_date)

#         df = df.filter(pl.col("Ageing") == ageing)

#         grouped = (
#             df.groupby(["Division", "Business Area"])
#               .agg(pl.col("Amount in Local Currency").sum().alias("Total Amount"))
#               .sort(["Division", "Business Area"])
#         )

#         return {"columns": grouped.columns, "rows": grouped.to_dicts()}
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# # -----------------------------
# # Drilldown IV: Vendor, Customer, Document Type
# # -----------------------------
# @app.get("/drilldown4")
# def drilldown_level_4(gl_account: str = Query(...), ageing: str = Query(...), division: str = Query(...), business_area: str = Query(...), current_date: str = Query(None)):
#     try:
#         df = pl.read_parquet(PARQUET_FILE)
#         if current_date is None:
#             current_date = datetime.now().strftime("%Y-%m-%d")

#         df = df.filter(pl.col("G/L Account") == gl_account)
#         df = derive_columns(df, current_date)

#         df = df.filter(
#             (pl.col("Ageing") == ageing) &
#             (pl.col("Division") == division) &
#             (pl.col("Business Area") == business_area)
#         )

#         def blank_to_others(col):
#             return pl.when(pl.col(col).is_null() | (pl.col(col).str.strip_chars() == ""))
#                    .then("Others")
#                    .otherwise(pl.col(col))

#         df = df.with_columns([
#             blank_to_others("Vendor Code").alias("Vendor Code"),
#             blank_to_others("Vendor Name").alias("Vendor Name"),
#             blank_to_others("Customer Code").alias("Customer Code"),
#             blank_to_others("Customer Name").alias("Customer Name"),
#             blank_to_others("Document Type").alias("Document Type")
#         ])

#         vendor_grouped = df.groupby(["Vendor Code", "Vendor Name"]).agg(
#             pl.col("Amount in Local Currency").sum().alias("Total Amount")
#         ).sort("Total Amount", descending=True)

#         customer_grouped = df.groupby(["Customer Code", "Customer Name"]).agg(
#             pl.col("Amount in Local Currency").sum().alias("Total Amount")
#         ).sort("Total Amount", descending=True)

#         doc_type_grouped = df.groupby("Document Type").agg(
#             pl.col("Amount in Local Currency").sum().alias("Total Amount")
#         ).sort("Total Amount", descending=True)

#         return {
#             "vendors": vendor_grouped.to_dicts(),
#             "customers": customer_grouped.to_dicts(),
#             "document_types": doc_type_grouped.to_dicts()
#         }

#     except Exception as e:
#         return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


