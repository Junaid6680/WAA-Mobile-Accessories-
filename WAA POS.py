import streamlit as st
import pandas as pd

# پیج کی سیٹنگ
st.set_page_config(page_title="WAA MOBILE - Dashboard", layout="wide")

# CSS تاکہ لک تصویر جیسی ہو جائے
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .sidebar .sidebar-content { background-color: #e3f2fd; }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar (Vouchers Menu) ---
st.sidebar.title("WAA MOBILE")
st.sidebar.subheader("Vouchers Menu")

menu_option = st.sidebar.radio(
    "Select Action:",
    ["Dashboard", "Cash Receive Voucher", "Cash Pay Voucher", "Bank Vouchers", "Expense Voucher"]
)

st.sidebar.markdown("---")
if st.sidebar.button("Day Summary"):
    st.write("Generating Day Summary...")

# --- Main Interface ---
st.title("📊 Business Management System")

# اوپر والے آئیکنز کی طرح کالمز
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("🛒 Sale"): st.info("Sale Section")
with col2:
    if st.button("📦 Purchase"): st.info("Purchase Section")
with col3:
    if st.button("📑 Inventory"): st.info("Stock Management")
with col4:
    if st.button("👥 Supplier"): st.info("Supplier Details")
with col5:
    if st.button("📊 Reports"): st.info("View Reports")

st.markdown("---")

# مینیو کے حساب سے پیج بدلنا
if menu_option == "Dashboard":
    st.subheader("Welcome to WAA MOBILE Dashboard")
    # یہاں آپ گراف یا ڈیٹا ٹیبل دکھا سکتے ہیں
    data = {'Description': ['Total Sales', 'Total Cash', 'Total Expense'], 'Amount': [50000, 25000, 5000]}
    df = pd.DataFrame(data)
    st.table(df)

elif menu_option == "Cash Receive Voucher":
    st.subheader("Cash Receive Entry")
    with st.form("receive_form"):
        name = st.text_input("Customer Name")
        amount = st.number_input("Amount", min_value=0)
        date = st.date_input("Date")
        submit = st.form_submit_button("Save Voucher")
        if submit:
            st.success(f"Voucher saved for {name}!")

# فوٹر
st.sidebar.info("Contact: 03209447950")
