import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
from datetime import datetime

# Invoice setup
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", 'B', 16)
pdf.cell(40, 10, "WAA Mobile Accessories")

# Streamlit UI
st.title("WAA Mobile Accessories")
st.write("Welcome to your billing system!")

if st.button("Generate Bill"):
    pdf.output("bill.pdf")
    st.success("Bill Generated!")
    with open("bill.pdf", "rb") as f:
        st.download_button("Download Bill", f, file_name="bill.pdf")
