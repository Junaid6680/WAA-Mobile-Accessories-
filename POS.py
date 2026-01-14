import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# ---------- CONFIG ----------
st.set_page_config("WAA POS", layout="wide")
DB = "waa_full_pos.db"

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Tables for Inventory, Invoices, Payments, Expenses, Suppliers and Permanent Customers
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT, bank_name TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS expenses(date TEXT, title TEXT, amount INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS suppliers(name TEXT PRIMARY KEY, balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)") # Permanent Customers
conn.commit()

# --- Sample Data ---
sample_items = [("iPhone 13 Case", 50, 800), ("Type-C Fast Charger", 30, 1200), ("Airpods Pro Gen 2", 15, 4500)]
for i, q, p in sample_items:
    c.execute("INSERT OR IGNORE INTO inventory VALUES(?,?,?)", (i, q, p))
conn.commit()

# ---------- HEADER ----------
st.markdown(f"## WAA Mobile Accessories")
tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory & Suppliers", "👥 Permanent Customers", "💰 Receiving", "💸 Expenses", "📊 Business Reports"])

# ================= 3. PERMANENT CUSTOMERS (New Tab) =================
with tabs[2]:
    st.subheader("👥 Manage Permanent Customers")
    c_name = st.text_input("Customer Name (e.g. Junaid Mobile)")
    c_bal = st.number_input("Opening Balance (Purane paise jo lene hain)", min_value=0)
    
    if st.button("Save Customer"):
        if c_name:
            c.execute("INSERT OR REPLACE INTO customers VALUES(?,?)", (c_name, c_bal))
            conn.commit()
            st.success(f"Customer '{c_name}' saved successfully!")
    
    st.write("### All Permanent Customers:")
    cust_df = pd.read_sql("SELECT * FROM customers", conn)
    st.dataframe(cust_df, use_container_width=True)

# ================= 4. RECEIVING (Bank & Ledger Update) =================
with tabs[3]:
    st.subheader("📥 Receive Payment")
    # Dropdown from permanent customers + Walk-in option
    all_custs = ["Walk-in"] + (cust_df["name"].tolist() if not cust_df.empty else [])
    r_cust = st.selectbox("Select Customer", all_custs)
    
    r_method = st.selectbox("Payment Method", ["Cash", "Meezan Bank", "Faysal Bank", "EasyPaisa", "JazzCash"])
    r_amt = st.number_input("Amount Received", min_value=0)
    
    if st.button("Record Payment"):
        if r_amt > 0:
            b_name = r_method if "Bank" in r_method else ""
            m_type = "Bank Transfer" if b_name else r_method
            c.execute("INSERT INTO payments VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_cust, r_amt, m_type, b_name))
            conn.commit()
            st.success(f"Received Rs. {r_amt} from {r_cust} in {r_method}")

# ================= 6. REPORTS (Ledger Hisab) =================
with tabs[5]:
    st.subheader("📊 Customer Ledger (Udhaar Hisab)")
    
    if not cust_df.empty:
        ledger_data = []
        for index, row in cust_df.iterrows():
            name = row['name']
            op_bal = row['opening_balance']
            
            # Total Sales to this customer
            total_sale = pd.read_sql(f"SELECT SUM(total) FROM invoices WHERE customer='{name}'", conn).iloc[0,0] or 0
            # Total Payments from this customer
            total_paid = pd.read_sql(f"SELECT SUM(amount) FROM payments WHERE customer='{name}'", conn).iloc[0,0] or 0
            
            current_bal = op_bal + total_sale - total_paid
            ledger_data.append({"Customer": name, "Old Balance": op_bal, "New Sales": total_sale, "Total Paid": total_paid, "Remaining": current_bal})
        
        st.table(pd.DataFrame(ledger_data))

    st.markdown("---")
    st.subheader("💰 Cash & Bank Summary")
    # (Pichle code wala Cash/Bank summary yahan ayega)
