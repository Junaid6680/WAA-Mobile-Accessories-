import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="WAA Mobile POS", layout="wide")

# Shop Details
SHOP_NAME = "WAA Mobile Accessories"
SHOP_INFO = "Ferozewala, Punjab | Contact: 0300-xxxxxxx"

st.title(f"📱 {SHOP_NAME} - POS System")

# --- Input Fields ---
col1, col2 = st.columns(2)
with col1:
    customer_name = st.text_input("Customer Name", "Walk-in Customer")
    item_name = st.text_input("Item Name")
with col2:
    price = st.number_input("Price per Item", min_value=0, value=0)
    qty = st.number_input("Quantity", min_value=1, value=1)

total_amount = price * qty
st.subheader(f"Total Amount: Rs. {total_amount}")

# --- Generate Bill Logic ---
if st.button("Generate & Download PDF Bill"):
    if item_name == "":
        st.error("Please enter Item Name first!")
    else:
        # PDF Creation
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", 'B', 20)
        pdf.cell(0, 10, SHOP_NAME, ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 5, SHOP_INFO, ln=True, align='C')
        pdf.ln(10)
        
        # Bill Info
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Customer: {customer_name}", ln=True)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True)
        pdf.ln(5)
        
        # Table Header
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(90, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Qty", 1, 0, 'C', True)
        pdf.cell(30, 10, "Price", 1, 0, 'C', True)
        pdf.cell(40, 10, "Total", 1, 1, 'C', True)
        
        # Table Data
        pdf.set_font("Arial", '', 12)
        pdf.cell(90, 10, item_name, 1)
        pdf.cell(30, 10, str(qty), 1, 0, 'C')
        pdf.cell(30, 10, str(price), 1, 0, 'C')
        pdf.cell(40, 10, str(total_amount), 1, 1, 'C')
        
        # Grand Total
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(150, 10, "Grand Total: ", 0, 0, 'R')
        pdf.cell(40, 10, f"Rs. {total_amount}", 1, 1, 'C')
        
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, "Thank you for your business! - WAA Mobile", 0, 1, 'C')

        # Output PDF
        file_name = f"Bill_{datetime.now().strftime('%H%M%S')}.pdf"
        pdf.output(file_name)
        
        with open(file_name, "rb") as f:
            st.download_button("Click here to Download Bill", f, file_name=file_name)
        st.success("Bill generated successfully!")
