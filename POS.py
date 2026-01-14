import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# ---------- CONFIG ----------
st.set_page_config("WAA POS", layout="wide")

SHOP_NAME = "WAA Mobile Accessories"
SHOP_ADDRESS = "Shop No T27, 3rd Floor, Hassan Center 2, Hall Road Lahore"
SHOP_CONTACT = "M Waqas 03154899075 | Farid Khan 03284080860 | Farman Ali 03030075400"

ADMIN_USER = "admin"
ADMIN_PASS = "1234"
DB = "waa_full_pos.db"

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Sare Tables Ensure Karein
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT, bank_name TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS expenses(date TEXT, title TEXT, amount INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS suppliers(name TEXT PRIMARY KEY, balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
conn.commit()

# Sample Inventory (Agar empty ho to)
c.execute("SELECT COUNT(*) FROM inventory")
if c.fetchone()[0] == 0:
    sample_items = [("iPhone 13 Case", 50, 800), ("Type-C Fast Charger", 30, 1200), ("Airpods Pro Gen 2", 15, 4500)]
    c.executemany("INSERT INTO inventory VALUES(?,?,?)", sample_items)
    conn.commit()

# ---------- LOGIN LOGIC ----------
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 WAA POS Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Ghalt Username ya Password!")
    st.stop()

# ---------- HEADER ----------
st.title(f"🏬 {SHOP_NAME}")
st.write(f"📍 {SHOP_ADDRESS} | 📞 {SHOP_CONTACT}")
st.markdown("---")

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory & Suppliers", "👥 Permanent Customers", "💰 Receiving", "💸 Expenses", "📊 Business Reports"])

# ================= 1. SALE INVOICE =================
with tabs[0]:
    st.subheader("New Sale")
    # Fetching Customers for dropdown
    cust_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    
    col_a, col_b = st.columns(2)
    with col_a: s_date = st.date_input("Date", datetime.now())
    with col_b: customer = st.selectbox("Select Customer", cust_list)
    
    inv_data = pd.read_sql("SELECT * FROM inventory", conn)
    c1, c2 = st.columns(2)
    with c1: item_select = st.selectbox("Item", inv_data["item"]) if not inv_data.empty else None
    with c2: qty = st.number_input("Qty", min_value=1, value=1)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    
    if st.button("➕ Add to Cart"):
        price = inv_data.loc[inv_data.item == item_select, "price"].values[0]
        st.session_state.cart.append({"Item": item_select, "Qty": qty, "Price": price, "Total": qty*price})
        st.success("Item Added!")
        st.rerun()

    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        if st.button("💾 Finalize Bill"):
            last_no = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000
            new_no = last_no + 1
            total_bill = sum(x['Total'] for x in st.session_state.cart)
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (new_no, s_date.strftime("%Y-%m-%d"), customer, total_bill))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            st.session_state.cart = []
            st.success(f"Bill #{new_no} Saved!")
            st.rerun()

# ================= 3. PERMANENT CUSTOMERS =================
with tabs[2]:
    st.subheader("👥 Add Permanent Customers")
    new_c = st.text_input("Customer Name")
    op_b = st.number_input("Opening Balance", min_value=0)
    if st.button("Save Permanent Customer"):
        c.execute("INSERT OR REPLACE INTO customers VALUES(?,?)", (new_c, op_b))
        conn.commit()
        st.success("Customer Saved!")
        st.rerun()

# ================= 4. RECEIVING (Banks Added) =================
with tabs[3]:
    st.subheader("📥 Receive Payment")
    r_cust = st.selectbox("From Customer", cust_list, key="rec_cust")
    r_amt = st.number_input("Amount Received", min_value=0)
    r_method = st.selectbox("Method", ["Cash", "Meezan Bank", "Faysal Bank", "EasyPaisa", "JazzCash"])
    
    if st.button("Save Payment"):
        b_name = r_method if "Bank" in r_method else ""
        c.execute("INSERT INTO payments VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_cust, r_amt, r_method, b_name))
        conn.commit()
        st.success("Payment Recorded!")

# ================= 6. REPORTS (Cash & Bank Summary) =================
with tabs[5]:
    st.subheader("📊 Business Summary")
    
    # Simple calculation for Cash/Bank
    cash = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Cash'", conn).iloc[0,0] or 0
    meezan = pd.read_sql("SELECT SUM(amount) FROM payments WHERE bank_name='Meezan Bank'", conn).iloc[0,0] or 0
    faysal = pd.read_sql("SELECT SUM(amount) FROM payments WHERE bank_name='Faysal Bank'", conn).iloc[0,0] or 0
    exps = pd.read_sql("SELECT SUM(amount) FROM expenses", conn).iloc[0,0] or 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💵 Cash in Hand", f"Rs {cash - exps}")
    c2.metric("🏦 Meezan Bank", f"Rs {meezan}")
    c3.metric("🏦 Faysal Bank", f"Rs {faysal}")
