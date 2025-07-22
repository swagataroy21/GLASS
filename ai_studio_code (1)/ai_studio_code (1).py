import polars as pl
from datetime import datetime

def process_uploaded_file(csv_path: str, mapping_path: str):
    """
    Processes the uploaded ACDOCA data and merges it with the division mapping.
    """
    try:
        # Load the main dataset using Polars
        df = pl.read_csv(csv_path, separator=';', infer_schema_length=10000, ignore_errors=True)

        # Clean column names (remove spaces, convert to uppercase)
        df.columns = [col.strip().upper() for col in df.columns]
        
        # Load the mapping table
        mapping_df = pl.read_excel(mapping_path)
        mapping_df.columns = [col.strip().upper() for col in mapping_df.columns]
        mapping_df = mapping_df.rename({"BUSINESS AREA": "RBUSA"})

        # Perform the join
        df = df.join(mapping_df, on='RBUSA', how='left')
        
        # Fill missing divisions with 'Others'
        df = df.with_columns(pl.col('DIVISION').fill_null('Others'))

        return df
    except Exception as e:
        print(f"An error occurred during data processing: {e}")
        return None

def get_gl_vs_ageing(df: pl.DataFrame, gl_account: str):
    """
    Generates the 'Selected GL vs Ageing' table aggregation.
    """
    return df.filter(pl.col('RACCT') == gl_account) \
             .group_by('Ageing') \
             .agg(pl.col('HSL').sum().alias('Amount')) \
             .sort('Ageing') \
             .to_dicts()

def get_gl_vs_division(df: pl.DataFrame, gl_account: str):
    """
    Generates the 'Selected GL vs Division' table aggregation.
    """
    return df.filter(pl.col('RACCT') == gl_account) \
             .group_by('Division') \
             .agg(pl.col('HSL').sum().alias('Amount')) \
             .sort('Division') \
             .to_dicts()