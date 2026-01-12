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
SHOP_CONTACT = "M Waqas 03154899075 | Farid Khan 03284080860 | Farman Ali 03030075400"

ADMIN_USER = "admin"
ADMIN_PASS = "1234"
DB = "waa_full_pos.db"

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS expenses(date TEXT, title TEXT, amount INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS partner_ledger(date TEXT, partner_name TEXT, type TEXT, amount INTEGER, remarks TEXT)")
conn.commit()

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

# ---------- LOGO LOGIC ----------
logo_path = "Logo.png" if os.path.exists("Logo.png") else ("logo.png" if os.path.exists("logo.png") else None)

# ---------- HEADER ----------
col_l, col_r = st.columns([1, 4])
with col_l:
    if logo_path: st.image(logo_path, width=120)
with col_r:
    st.markdown(f"## {SHOP_NAME}")
    st.caption(f"📍 {SHOP_ADDRESS} | 📞 {SHOP_CONTACT}")

st.markdown("---")

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "📝 Khata (Ledger)", "💸 Shop Expenses", "🤝 Capital Account", "📊 Business Reports"])

# ================= 1. SALE INVOICE (With Editable Date & Auto Inv) =================
with tabs[0]:
    st.subheader("New Sale")
    col_a, col_b = st.columns(2)
    with col_a:
        sale_date = st.date_input("Invoice Date", datetime.now())
    with col_b:
        customer = st.text_input("Customer Name", value="Walk-in")
    
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    c1, c2 = st.columns(2)
    with c1: item = st.selectbox("Select Item", inv_df["item"]) if not inv_df.empty else None
    with c2: qty = st.number_input("Qty", min_value=1, value=1)
    
    if "cart_sale" not in st.session_state: st.session_state.cart_sale = []

    if st.button("➕ Add Item"):
        price = inv_df.loc[inv_df.item==item, "price"].values[0]
        st.session_state.cart_sale.append({"item": item, "qty": qty, "price": price, "total": qty*price})
    
    if st.session_state.cart_sale:
        st.table(pd.DataFrame(st.session_state.cart_sale))
        if st.button("💾 Generate Bill"):
            last_no = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000
            new_no = last_no + 1
            total_bill = sum(x['total'] for x in st.session_state.cart_sale)
            
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (new_no, sale_date.strftime("%Y-%m-%d"), customer, total_bill))
            for r in st.session_state.cart_sale:
                c.execute("UPDATE inventory SET qty=qty-? WHERE item=?", (r['qty'], r['item']))
            conn.commit()
            
            # Simple PDF Generation
            pdf = FPDF()
            pdf.add_page()
            if logo_path: pdf.image(logo_path, 10, 8, 30)
            pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, SHOP_NAME, ln=True, align="C")
            pdf.set_font("Arial", size=10); pdf.cell(0, 5, f"Inv: {new_no} | Date: {sale_date}", ln=True, align="C")
            pdf.ln(10)
            for r in st.session_state.cart_sale:
                pdf.cell(100, 8, f"{r['item']} x {r['qty']}", 0)
                pdf.cell(0, 8, f"Rs {r['total']}", 0, ln=True, align="R")
            pdf.output(f"Bill_{new_no}.pdf")
            
            st.session_state.cart_sale = []
            st.success(f"Invoice {new_no} Saved!")
            st.rerun()

# ================= 4. SHOP EXPENSES (Editable Date) =================
with tabs[3]:
    st.subheader("💸 Shop Expenses")
    col1, col2 = st.columns(2)
    with col1: exp_date = st.date_input("Expense Date", datetime.now())
    with col2: exp_t = st.text_input("Expense Detail")
    exp_a = st.number_input("Amount", min_value=0, value=0)
    if st.button("Save Expense"):
        c.execute("INSERT INTO expenses VALUES(?,?,?)", (exp_date.strftime("%Y-%m-%d"), exp_t, exp_a))
        conn.commit()
        st.success("Expense Added!")

# ================= 5. CAPITAL ACCOUNT (Editable Date) =================
with tabs[4]:
    st.subheader("🤝 Partners Capital")
    p_date = st.date_input("Record Date", datetime.now())
    p_names = ["M Waqas", "Farid Khan", "Farman Ali"]
    p_name = st.selectbox("Partner", p_names)
    p_type = st.selectbox("Type", ["Investment (In)", "Withdrawal (Out)"])
    p_amt = st.number_input("PKR Amount", min_value=0, value=0)
    if st.button("Save Capital Entry"):
        c.execute("INSERT INTO partner_ledger VALUES(?,?,?,?,?)", (p_date.strftime("%Y-%m-%d"), p_name, p_type, p_amt, "Update"))
        conn.commit()
        st.success("Capital Account Updated!")

# ================= 6. REPORTS (Date Range Filter) =================
with tabs[5]:
    st.subheader("📊 Profit/Loss Report")
    col_s, col_e = st.columns(2)
    start_d = col_s.date_input("Start Date", datetime(2024, 1, 1))
    end_d = col_e.date_input("End Date", datetime.now())
    
    # Filtered Data
    mask = f"date BETWEEN '{start_d}' AND '{end_d}'"
    sales = pd.read_sql(f"SELECT SUM(total) FROM invoices WHERE {mask}", conn).iloc[0,0] or 0
    exps = pd.read_sql(f"SELECT SUM(amount) FROM expenses WHERE {mask}", conn).iloc[0,0] or 0
    
    st.metric("Total Sales", f"Rs {sales}")
    st.metric("Total Expenses", f"Rs {exps}")
    st.metric("Net Profit", f"Rs {sales - exps}")
