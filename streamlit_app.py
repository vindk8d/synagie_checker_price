import streamlit as st
import pandas as pd
import tempfile
from bs4 import BeautifulSoup
import io
import time
import re
from functools import lru_cache

# Set page config for better performance
st.set_page_config(
    page_title="HTML to CSV Price Checker",
    page_icon="📊",
    layout="wide"
)

# Initialize session state for caching
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'result_df' not in st.session_state:
    st.session_state.result_df = None

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
        st.error(f"Error converting HTML to text: {str(e)}")
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

def validate_csv_structure(df1, df2):
    """Validate the structure of both files with improved error handling."""
    df1_columns = df1.columns.tolist()
    df2_columns = df2.columns.tolist()
    
    if len(df1_columns) < 2:
        raise ValueError("First file must have at least 2 columns (product number and HTML content)")
    if len(df2_columns) < 4:
        raise ValueError("Second file must have at least 4 columns (product number and description in 4th column)")
    
    return df1_columns[0], df1_columns[1], df2_columns[1], df2_columns[3]

# Cache expensive operations
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(file):
    """Load and cache file data."""
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

@st.cache_data(ttl=3600)
def process_batch(batch_df, df2, product_col1, html_col, product_col2, desc_col):
    """Process a batch of rows."""
    processed_data = []
    for _, row in batch_df.iterrows():
        try:
            product_number = row[product_col1]
            html_content = row[html_col]
            text_content = html_to_text(html_content)
            
            matching_product = df2[df2[product_col2] == product_number]
            if not matching_product.empty:
                product_description = matching_product.iloc[0][desc_col]
                prices1 = extract_prices(text_content)
                prices2 = extract_prices(product_description)
                processed_data.append([
                    product_number,
                    text_content,
                    product_description,
                    prices1,
                    prices2
                ])
        except Exception as e:
            continue
    return processed_data

st.title("HTML to CSV Price Checker (Streamlit)")

st.write("Upload two CSV files to compare and extract prices.")

# File uploaders
col1, col2 = st.columns(2)
with col1:
    file1 = st.file_uploader("First File (HTML Content)", type=["csv", "xlsx", "xls"])
with col2:
    file2 = st.file_uploader("Second File (Product Descriptions)", type=["csv", "xlsx", "xls"])

if file1 and file2:
    try:
        # Show loading spinner while reading files
        with st.spinner('Reading files...'):
            df1 = load_data(file1)
            df2 = load_data(file2)

        # Validate and get columns
        product_col1, html_col, product_col2, desc_col = validate_csv_structure(df1, df2)

        # Process button
        if st.button("Process Files"):
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Process in batches
            batch_size = 100
            total_rows = len(df1)
            processed_data = []
            
            for i in range(0, total_rows, batch_size):
                batch_df = df1.iloc[i:i+batch_size]
                batch_results = process_batch(batch_df, df2, product_col1, html_col, product_col2, desc_col)
                processed_data.extend(batch_results)
                
                # Update progress
                progress = min((i + batch_size) / total_rows, 1.0)
                progress_bar.progress(progress)
                status_text.text(f"Processing rows {i+1} to {min(i+batch_size, total_rows)} of {total_rows}")
                
                # Add a small delay to allow UI updates
                time.sleep(0.1)

            if processed_data:
                # Store in session state
                st.session_state.processed_data = processed_data
                st.session_state.result_df = pd.DataFrame(processed_data, columns=[
                    'Product Number',
                    'Natural Language Output',
                    'Product Description',
                    'LAZADA PRICES',
                    'SHOPEE PRICES'
                ])
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Display results
                st.success("Processing complete!")
                st.dataframe(st.session_state.result_df)
                
                # Download button
                csv = st.session_state.result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download results as CSV",
                    data=csv,
                    file_name='comparison_results.csv',
                    mime='text/csv',
                )
            else:
                st.warning("No matching products found or no data processed.")
    except Exception as e:
        st.error(f"Error processing files: {e}") 