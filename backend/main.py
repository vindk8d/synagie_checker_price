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
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import threading

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

# Thread pool for parallel processing
thread_pool = ThreadPoolExecutor(max_workers=4)

# Cache for HTML parsing and price extraction
@lru_cache(maxsize=1000)
def html_to_text(html_content):
    """Convert HTML to text with caching for better performance."""
    try:
        # Use lxml parser for better performance
        soup = BeautifulSoup(html_content, 'lxml')
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        # Get text and normalize whitespace
        text = soup.get_text(separator=' ', strip=True)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text
    except Exception as e:
        logger.error(f"Error converting HTML to text: {str(e)}")
        return str(html_content)

# Compile regex pattern once for better performance
PRICE_PATTERN = re.compile(
    r'(?:(?:[\$₱£€¥₹]|(?:PHP|USD|EUR|GBP|JPY|INR))\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:[\$₱£€¥₹]|(?:PHP|USD|EUR|GBP|JPY|INR)))',
    re.IGNORECASE
)

@lru_cache(maxsize=1000)
def extract_prices(text):
    """Extract prices from text with caching for better performance."""
    if not text:
        return ''
    prices = PRICE_PATTERN.findall(text)
    return ' | '.join(prices) if prices else ''

def process_row(args):
    """Process a single row of data."""
    row, product_col1, html_col, df2, product_col2, desc_col = args
    try:
        product_number = row[product_col1]
        html_content = row[html_col]
        text_content = html_to_text(html_content)
        
        matching_product = df2[df2[product_col2] == product_number]
        if not matching_product.empty:
            product_description = matching_product.iloc[0][desc_col]
            prices1 = extract_prices(text_content)
            prices2 = extract_prices(product_description)
            return [
                product_number,
                text_content,
                product_description,
                prices1,
                prices2
            ]
    except Exception as e:
        logger.error(f"Error processing row: {str(e)}")
    return None

def validate_csv_structure(df1, df2):
    """Validate the structure of both files with improved error handling."""
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
        
        # Read files into DataFrames
        df1 = pd.read_csv(file1.file) if file1.filename.endswith(".csv") else pd.read_excel(file1.file)
        df2 = pd.read_csv(file2.file) if file2.filename.endswith(".csv") else pd.read_excel(file2.file)
        
        # Validate file structure and get column names
        product_col1, html_col, product_col2, desc_col = validate_csv_structure(df1, df2)
        
        # Prepare arguments for parallel processing
        process_args = [(row, product_col1, html_col, df2, product_col2, desc_col) 
                       for _, row in df1.iterrows()]
        
        # Process rows in parallel
        processed_data = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(process_row, process_args))
            processed_data = [r for r in results if r is not None]
        
        if not processed_data:
            logger.error("No data was processed successfully")
            raise HTTPException(status_code=400, detail="No data was processed successfully")
        
        # Create new DataFrame with processed data
        result_df = pd.DataFrame(processed_data, columns=[
            'Product Number',
            'Natural Language Output',
            'Product Description',
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
    except Exception as e:
        logger.error(f"Error in process_csv: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 