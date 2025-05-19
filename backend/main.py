from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
from bs4 import BeautifulSoup
import io
import tempfile
import os
from difflib import unified_diff
import logging
import csv
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS with more specific settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app's origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

@app.get("/")
async def health_check():
    return JSONResponse({"status": "ok", "message": "Server is running"})

def html_to_text(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        logger.error(f"Error converting HTML to text: {str(e)}")
        return str(html_content)

def extract_prices(text):
    """Extract prices (numbers with currency symbols) from text."""
    # Pattern to match currency formats:
    # Must start with currency symbol or have currency symbol after the number
    # Supports formats like $50, 50$, PHP 50, 50 PHP, ₱50, 50₱
    price_pattern = r'(?:(?:[\$₱£€¥₹]|(?:PHP|USD|EUR|GBP|JPY|INR))\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:[\$₱£€¥₹]|(?:PHP|USD|EUR|GBP|JPY|INR)))'
    prices = re.findall(price_pattern, text, re.IGNORECASE)
    return ' | '.join(prices) if prices else ''

def get_differences(text1, text2):
    try:
        # Extract prices from both texts
        prices1 = extract_prices(text1)
        prices2 = extract_prices(text2)
        
        # Split texts into words for better comparison
        words1 = text1.split()
        words2 = text2.split()
        
        # Generate differences
        diff = list(unified_diff(words1, words2, n=0))
        
        # Filter out the header lines and format the differences
        diff = [line for line in diff if not line.startswith('@@') and not line.startswith('---') and not line.startswith('+++')]
        
        # Join the differences with spaces
        return ' '.join(diff), prices1, prices2
    except Exception as e:
        logger.error(f"Error getting differences: {str(e)}")
        return "Error comparing texts", "", ""

def find_header_row(contents, required_columns, file_extension):
    """Scan the first 20 rows to find the header row containing all required columns."""
    if file_extension == 'csv':
        lines = contents.decode('utf-8').splitlines()
        reader = csv.reader(lines)
        for idx, row in enumerate(reader):
            if all(col in row for col in required_columns):
                logger.info(f"Detected header row at line {idx}: {row}")
                return idx
            if idx > 20:
                break
    else:  # Excel
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(contents), read_only=True)
        ws = wb.active
        for idx, row in enumerate(ws.iter_rows(values_only=True)):
            if row and all(col in row for col in required_columns):
                logger.info(f"Detected header row at line {idx}: {row}")
                return idx
            if idx > 20:
                break
    logger.warning("Header row not found, defaulting to first row.")
    return 0

async def read_file(file: UploadFile, required_columns=None) -> pd.DataFrame:
    """Read either CSV or XLSX file into a pandas DataFrame, auto-detecting the header row."""
    contents = await file.read()
    file_extension = file.filename.split('.')[-1].lower()
    if required_columns is None:
        required_columns = []
    try:
        header_row = 0
        if required_columns:
            header_row = find_header_row(contents, required_columns, file_extension)
        if file_extension == 'csv':
            return pd.read_csv(io.StringIO(contents.decode('utf-8')), header=header_row)
        elif file_extension == 'xlsx':
            return pd.read_excel(io.BytesIO(contents), engine='openpyxl', header=header_row)
        elif file_extension == 'xls':
            return pd.read_excel(io.BytesIO(contents), engine='xlrd', header=header_row)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}. Please upload a CSV or XLSX file.")
    except Exception as e:
        logger.error(f"Error reading file {file.filename}: {str(e)}")
        raise Exception(f"Error reading file {file.filename}: {str(e)}")

def validate_csv_structure(df1, df2):
    """Validate the structure of both files"""
    df1_columns = df1.columns.tolist()
    df2_columns = df2.columns.tolist()
    
    logger.info(f"First file columns: {df1_columns}")
    logger.info(f"Second file columns: {df2_columns}")
    
    if len(df1_columns) < 2:
        raise ValueError("First file must have at least 2 columns (product number and HTML content)")
    if len(df2_columns) < 4:
        raise ValueError("Second file must have at least 4 columns (product number and description in 4th column)")
    
    return df1_columns[0], df1_columns[1], df2_columns[1], df2_columns[3]

@app.post("/process-csv")
async def process_csv(file1: UploadFile = File(...), file2: UploadFile = File(...)):
    try:
        logger.info("Starting file processing")
        logger.info(f"Received files: {file1.filename}, {file2.filename}")
        
        if not file1 or not file2:
            raise HTTPException(status_code=400, detail="Both files are required")
        
        # Define required columns for each file
        required_columns1 = ["Product ID"]  # for file1 (HTML content)
        required_columns2 = ["Product ID", "Product Description"]  # for file2 (Descriptions)
        
        # Read the first file (HTML content)
        logger.info(f"Reading first file: {file1.filename}")
        df1 = await read_file(file1, required_columns=required_columns1)
        logger.info(f"First file size: {len(df1)} rows")
        
        # Read the second file (Product descriptions)
        logger.info(f"Reading second file: {file2.filename}")
        df2 = await read_file(file2, required_columns=required_columns2)
        logger.info(f"Second file size: {len(df2)} rows")
        
        # Validate file structure and get column names
        try:
            product_col1, html_col, product_col2, desc_col = validate_csv_structure(df1, df2)
        except ValueError as e:
            logger.error(f"File structure validation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Process HTML content
        processed_data = []
        success_count = 0
        error_count = 0
        
        for index, row in df1.iterrows():
            try:
                product_number = row[product_col1]
                html_content = row[html_col]
                text_content = html_to_text(html_content)
                
                # Find matching product in second file
                matching_product = df2[df2[product_col2] == product_number]
                if not matching_product.empty:
                    product_description = matching_product.iloc[0][desc_col]
                    differences, prices1, prices2 = get_differences(text_content, product_description)
                    
                    processed_data.append([
                        product_number,
                        text_content,
                        product_description,
                        differences,
                        prices1,
                        prices2
                    ])
                    success_count += 1
                else:
                    logger.warning(f"No matching product found for {product_number}")
                    error_count += 1
            except Exception as e:
                logger.error(f"Error processing row {index}: {str(e)}")
                error_count += 1
                continue
        
        if not processed_data:
            logger.error("No data was processed successfully")
            raise HTTPException(status_code=400, detail="No data was processed successfully")
        
        logger.info(f"Processing complete. Successfully processed {success_count} rows, {error_count} errors.")
        
        # Create new DataFrame with processed data
        result_df = pd.DataFrame(processed_data, columns=[
            'Product Number',
            'Natural Language Output',
            'Product Description',
            'Differences',
            'LAZADA PRICES',
            'SHOPEE PRICES'
        ])
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        result_df.to_csv(temp_file.name, index=False)
        logger.info(f"Results saved to {temp_file.name}")
        
        return FileResponse(
            temp_file.name,
            media_type='text/csv',
            filename='comparison_results.csv',
            background=None
        )
    except HTTPException as he:
        logger.error(f"HTTP Exception: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Error in process_csv: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 