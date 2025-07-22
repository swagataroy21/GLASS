from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from services.data_processing import process_uploaded_file, get_gl_vs_ageing, get_gl_vs_division
from services.ai_summary import generate_summary
import polars as pl
import os
import shutil

router = APIRouter()
UPLOAD_DIRECTORY = "temp_uploads"

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# In-memory cache for the DataFrame (for simplicity)
# In a production app, consider using Redis or another proper cache/database
df_cache = {"data": None, "filename": None}

def cleanup_file(filepath: str):
    """Remove the file after a delay."""
    if os.path.exists(filepath):
        os.remove(filepath)

@router.post("/uploadfile/")
async def create_upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")

    file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
    
    try:
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        df = process_uploaded_file(file_location, "division_mapping.xlsx")
        if df is None:
            raise HTTPException(status_code=400, detail="Error processing file. Check file format and content.")
        
        # Cache the processed dataframe
        df_cache["data"] = df
        df_cache["filename"] = file.filename
        
        gl_accounts = df['RACCT'].unique().drop_nulls().to_list()
        
        # Clean up the uploaded file after processing
        background_tasks.add_task(cleanup_file, file_location)
        
        return {"message": f"Successfully uploaded and processed {file.filename}", "gl_accounts": gl_accounts}
    except Exception as e:
        # Also cleanup on error
        background_tasks.add_task(cleanup_file, file_location)
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@router.post("/analyze/")
async def analyze_data(gl_account: str = Form(...), analysis_date: str = Form(...)):
    if df_cache["data"] is None:
        raise HTTPException(status_code=400, detail="No data available. Please upload a file first.")

    df = df_cache["data"]
    
    # Add ageing column based on the analysis date
    df_with_ageing = df.with_columns(
        pl.col('BLDAT').str.to_date('%d.%m.%Y', strict=False).alias('PostingDate')
    ).with_columns(
        ((pl.lit(analysis_date).str.to_date('%Y-%m-%d') - pl.col('PostingDate')).dt.days()).alias('AgeInDays')
    ).with_columns(
        pl.when(pl.col('AgeInDays') < 180).then(pl.lit('<6 months'))
        .when((pl.col('AgeInDays') >= 180) & (pl.col('AgeInDays') < 365)).then(pl.lit('6 months to 1 year'))
        .when((pl.col('AgeInDays') >= 365) & (pl.col('AgeInDays') < 730)).then(pl.lit('1-2 years'))
        .when((pl.col('AgeInDays') >= 730) & (pl.col('AgeInDays') < 1095)).then(pl.lit('2-3 years'))
        .when((pl.col('AgeInDays') >= 1095) & (pl.col('AgeInDays') < 1825)).then(pl.lit('3-5 years'))
        .otherwise(pl.lit('>5 years'))
        .alias('Ageing')
    )

    gl_vs_ageing = get_gl_vs_ageing(df_with_ageing, gl_account)
    gl_vs_division = get_gl_vs_division(df_with_ageing, gl_account)

    ai_summary = generate_summary(gl_vs_ageing, gl_vs_division, gl_account)

    return {
        "gl_vs_ageing": gl_vs_ageing,
        "gl_vs_division": gl_vs_division,
        "ai_summary": ai_summary
    }