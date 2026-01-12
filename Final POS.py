import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import os

# ---------- CONFIG ----------
st.set_page_config("WAA POS", layout="wide")

SHOP_NAME = "WAA Mobile Accessories"
SHOP_ADDRESS = "Shop No T27, 3rd Floor, Hassan Center 2, Hall Road Lahore"
SHOP_CONTACT = "M Waqas 03154899075 | Farid Khan 03284080860"

ADMIN_USER = "admin"
ADMIN_PASS = "1234"
DB = "waa_full_pos.db"

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Existing Tables
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoice_items(inv_no INTEGER, item TEXT, qty INTEGER, price INTEGER, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS purchases(pur_no INTEGER, date TEXT, supplier TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS purchase_items(pur_no INTEGER, item TEXT, qty INTEGER, price INTEGER, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, party TEXT, type TEXT, method TEXT, amount INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS expenses(date TEXT, title TEXT, amount INTEGER)")

# New Table for Partners
c.execute("CREATE TABLE IF NOT EXISTS partner_ledger(date TEXT, partner_name TEXT, type TEXT, amount INTEGER, remarks TEXT)")
conn.commit()

# ---------- AUTO-IMPORT STOCK ----------
def auto_import_stock():
    check = c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    if check == 0:
        initial_stock = [
            ('USB Type-C Cable', 3000, 250), ('Micro-USB Cable', 2500, 200),
            ('Lightning Cable (iPhone)', 1500, 400), ('Wall Charger (5W)', 700, 500),
            ('Wall Charger (Fast Charging)', 500, 700), ('Car Charger', 660, 600),
            ('Power Bank 10000mAh', 300, 1500), ('Power Bank 20000mAh', 250, 3000),
            ('Silicone Case (Universal)', 2000, 150), ('Hard Case (Brand specific)', 1000, 250),
            ('Flip / Wallet Case', 500, 400), ('Tempered Glass (Universal)', 1800, 150),
            ('Full Body Screen Protector', 500, 300), ('Wired Earphones', 1500, 250),
            ('Bluetooth Earbuds', 700, 1200), ('Over-ear Headphones', 300, 2500),
            ('Bluetooth Speaker (Mini)', 250, 1800), ('Smart Watch', 150, 4000),
            ('Fitness Tracker', 300, 2200), ('Selfie Stick', 400, 500),
            ('Tripod Stand', 200, 900), ('Car Phone Holder', 500, 400),
            ('Pop Socket / Phone Grip', 800, 250), ('Rechargeable Battery', 100, 500),
            ('Mobile Repair Toolkit', 50, 1800), ('Replacement LCD / Screen', 40, 3500),
            ('OTG Adapter', 1000, 200), ('Stylus Pen', 300, 300), ('Cleaning Kit', 250, 100)
        ]
        c.executemany("INSERT OR REPLACE INTO inventory VALUES (?, ?, ?)", initial_stock)
        conn.commit()

auto_import_stock()

# ---------- LOGIN ----------
if "login" not in st.session_state: st.session_state.login = False
if not st.session_state.login:
    st.title("🔐 WAA POS Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.login = True
            st.rerun()
        else: st.error("Ghalt Password!")
    st.stop()

# ---------- HEADER ----------
st.markdown(f"<h2 style='text-align:center'>{SHOP_NAME}</h2><p style='text-align:center'>{SHOP_ADDRESS}<br>📞 {SHOP_CONTACT}</p><hr>", unsafe_allow_html=True)

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "📝 Khata (Ledger)", "💸 Daily Expenses", "🤝 Partners Khata", "📊 Business Reports"])

# ================= 1. SALE INVOICE =================
with tabs[0]:
    st.subheader("New Sale")
    customer = st.text_input("Customer Name", value="Walk-in")
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    col1, col2, col3 = st.columns(3)
    with col1: item = st.selectbox("Item Select", inv_df["item"]) if not inv_df.empty else None
    with col2: qty = st.number_input("Qty", min_value=1, value=1)
    if st.button("➕ Add to Cart"):
        if item:
            price = inv_df.loc[inv_df.item==item, "price"].values[0]
            if "cart" not in st.session_state: st.session_state.cart = []
            st.session_state.cart.append({"item": item, "qty": qty, "price": price, "total": qty*price})
    
    if "cart" in st.session_state and st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        if st.button("💾 Finalize & Print"):
            last_inv = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000
            new_no = last_inv + 1
            total_bill = sum(x['total'] for x in st.session_state.cart)
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (new_no, datetime.now().strftime("%Y-%m-%d"), customer, total_bill))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty=qty-? WHERE item=?", (r['qty'], r['item']))
            conn.commit()
            st.session_state.cart = []
            st.success("Sale Recorded!")

# ================= 2. INVENTORY =================
with tabs[1]:
    st.subheader("Current Stock")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# ================= 3. KHATA (LEDGER) =================
with tabs[2]:
    st.subheader("Customer & Supplier Khata")
    # Universal Ledger Logic (Same as previous)
    st.write("Record payments here...")

# ================= 4. DAILY EXPENSES =================
with tabs[3]:
    st.subheader("Daily Shop Expenses")
    exp_t = st.text_input("Expense Reason")
    exp_a = st.number_input("Amount", min_value=0)
    if st.button("Save Expense"):
        c.execute("INSERT INTO expenses VALUES(?,?,?)", (datetime.now().strftime("%Y-%m-%d"), exp_t, exp_a))
        conn.commit()
        st.rerun()

# ================= 5. PARTNERS KHATA =================
with tabs[4]:
    st.subheader("🤝 Partners Investment & Drawings")
    p_names = ["M Waqas", "Farid Khan", "Farman Ali"]
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        sel_partner = st.selectbox("Select Partner", p_names)
    with col_p2:
        trans_type = st.selectbox("Transaction Type", ["Investment (Paise Lagaye)", "Drawing (Shop se kharcha liya)"])
    with col_p3:
        p_amount = st.number_input("PKR Amount", min_value=0)
    
    p_rem = st.text_input("Remarks (e.g., Weekly Kharcha, New Stock Investment)")
    
    if st.button("Submit Partner Entry"):
        c.execute("INSERT INTO partner_ledger VALUES(?,?,?,?,?)", 
                  (datetime.now().strftime("%Y-%m-%d"), sel_partner, trans_type, p_amount, p_rem))
        conn.commit()
        st.success("Partner Khata Updated!")

    st.markdown("---")
    st.write("### Partners Summary")
    p_summary = pd.read_sql("""
        SELECT partner_name, 
        SUM(CASE WHEN type LIKE 'Investment%' THEN amount ELSE 0 END) as Total_Investment,
        SUM(CASE WHEN type LIKE 'Drawing%' THEN amount ELSE 0 END) as Total_Withdrawal
        FROM partner_ledger GROUP BY partner_name
    """, conn)
    p_summary['Current_Balance'] = p_summary['Total_Investment'] - p_summary['Total_Withdrawal']
    st.table(p_summary)

# ================= 6. BUSINESS REPORTS =================
with tabs[5]:
    st.subheader("📊 Profit / Loss & Business Health")
    
    # Simple Profit Calculation
    total_sales = pd.read_sql("SELECT SUM(total) FROM invoices", conn).iloc[0,0] or 0
    total_expenses = pd.read_sql("SELECT SUM(amount) FROM expenses", conn).iloc[0,0] or 0
    
    # Net Profit
    net_profit = total_sales - total_expenses
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sales", f"Rs {total_sales}")
    c2.metric("Shop Expenses", f"Rs {total_expenses}")
    
    if net_profit > 0:
        c3.metric("Net Profit", f"Rs {net_profit}", delta="PROFIT")
    else:
        c3.metric("Net Profit", f"Rs {net_profit}", delta="LOSS", delta_color="inverse")

    st.markdown("---")
    st.write("### ⚖️ Estimated Profit Sharing (3-Ways)")
    share = net_profit / 3
    st.info(f"Each Partner's Share in Current Profit: **Rs {round(share, 2)}**")
    
    st.write("#### Detailed Partner Logs")
    st.dataframe(pd.read_sql("SELECT * FROM partner_ledger ORDER BY date DESC", conn), use_container_width=True)
