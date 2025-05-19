import streamlit as st
import pandas as pd
import tempfile
from backend.main import html_to_text, extract_prices, validate_csv_structure
import io
from tqdm import tqdm

# Cache the expensive operations
@st.cache_data
def process_html_content(html_content):
    return html_to_text(html_content)

@st.cache_data
def process_prices(text_content):
    return extract_prices(text_content)

st.title("HTML to CSV Price Checker (Streamlit)")

st.write("Upload two CSV files to compare and extract prices.")

file1 = st.file_uploader("First File (HTML Content)", type=["csv", "xlsx", "xls"])
file2 = st.file_uploader("Second File (Product Descriptions)", type=["csv", "xlsx", "xls"])

if file1 and file2:
    try:
        # Read files into DataFrames
        df1 = pd.read_csv(file1) if file1.name.endswith(".csv") else pd.read_excel(file1)
        df2 = pd.read_csv(file2) if file2.name.endswith(".csv") else pd.read_excel(file2)

        # Validate and get columns
        product_col1, html_col, product_col2, desc_col = validate_csv_structure(df1, df2)

        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        processed_data = []
        total_rows = len(df1)
        
        # Process in batches of 100
        batch_size = 100
        for i in range(0, total_rows, batch_size):
            batch_df = df1.iloc[i:i+batch_size]
            
            for index, row in batch_df.iterrows():
                try:
                    product_number = row[product_col1]
                    html_content = row[html_col]
                    
                    # Use cached functions
                    text_content = process_html_content(html_content)
                    
                    matching_product = df2[df2[product_col2] == product_number]
                    if not matching_product.empty:
                        product_description = matching_product.iloc[0][desc_col]
                        prices1 = process_prices(text_content)
                        prices2 = process_prices(product_description)
                        processed_data.append([
                            product_number,
                            text_content,
                            product_description,
                            prices1,
                            prices2
                        ])
                except Exception as e:
                    continue
                
                # Update progress
                progress = (index + 1) / total_rows
                progress_bar.progress(progress)
                status_text.text(f"Processing row {index + 1} of {total_rows}")

        if processed_data:
            result_df = pd.DataFrame(processed_data, columns=[
                'Product Number',
                'Natural Language Output',
                'Product Description',
                'LAZADA PRICES',
                'SHOPEE PRICES'
            ])
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            st.write(result_df)
            csv = result_df.to_csv(index=False).encode('utf-8')
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