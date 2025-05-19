import streamlit as st
import pandas as pd
import tempfile
from backend.main import html_to_text, extract_prices, validate_csv_structure
import io

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

        processed_data = []
        for index, row in df1.iterrows():
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
        if processed_data:
            result_df = pd.DataFrame(processed_data, columns=[
                'Product Number',
                'Natural Language Output',
                'Product Description',
                'LAZADA PRICES',
                'SHOPEE PRICES'
            ])
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