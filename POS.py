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

# Sare Tables Ensure Karein
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT, bank_name TEXT)")
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

# ---------- LOGO ----------
logo_path = "Logo.png" if os.path.exists("Logo.png") else None

# ---------- HEADER ----------
col_l, col_r = st.columns([1, 4])
with col_l:
    if logo_path: st.image(logo_path, width=120)
with col_r:
    st.markdown(f"## {SHOP_NAME}")
    st.caption(f"📍 {SHOP_ADDRESS} | 📞 {SHOP_CONTACT}")

st.markdown("---")

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "💰 Khata & Receiving", "💸 Shop Expenses", "🤝 Capital Account", "📊 Business Reports"])

# ================= 1. SALE INVOICE =================
with tabs[0]:
    st.subheader("New Sale")
    col_a, col_b = st.columns(2)
    with col_a: s_date = st.date_input("Sale Date", datetime.now(), key="s_date")
    with col_b: customer = st.text_input("Customer Name", value="Walk-in")
    
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    c1, c2 = st.columns(2)
    with c1: item = st.selectbox("Select Item", inv_df["item"]) if not inv_df.empty else None
    with c2: qty = st.number_input("Qty", min_value=1, value=1)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    if st.button("➕ Add to Cart"):
        p = inv_df.loc[inv_df.item==item, "price"].values[0]
        st.session_state.cart.append({"item": item, "qty": qty, "price": p, "total": qty*p})
    
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        if st.button("❌ Clear/Edit Cart"):
            st.session_state.cart = []
            st.rerun()
        if st.button("💾 Save & Print Bill"):
            l_no = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000
            new_no = l_no + 1
            total = sum(x['total'] for x in st.session_state.cart)
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (new_no, s_date.strftime("%Y-%m-%d"), customer, total))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty=qty-? WHERE item=?", (r['qty'], r['item']))
            conn.commit()
            st.session_state.cart = []
            st.success(f"Bill #{new_no} Saved!")

# ================= 3. KHATA & RECEIVING (With Bank Selection) =================
with tabs[2]:
    st.subheader("📥 Receive Payment")
    col1, col2 = st.columns(2)
    with col1: r_date = st.date_input("Date", datetime.now(), key="r_date")
    with col2: r_cust = st.text_input("Customer Name", key="r_cust")
    
    r_amt = st.number_input("Amount", min_value=0)
    r_method = st.selectbox("Method", ["Cash", "Bank Transfer", "EasyPaisa", "JazzCash"])
    
    # Bank Account Detail if Bank Transfer selected
    bank_name = ""
    if r_method == "Bank Transfer":
        bank_name = st.text_input("Bank Name (e.g. Meezan, HBL, Allied)", placeholder="Enter Bank Name")

    if st.button("Record Payment"):
        if r_cust and r_amt > 0:
            c.execute("INSERT INTO payments VALUES(?,?,?,?,?)", (r_date.strftime("%Y-%m-%d"), r_cust, r_amt, r_method, bank_name))
            conn.commit()
            st.success("Payment Received Successfully!")
        else: st.warning("Naam aur Amount lazmi likhen.")

# ================= 4. SHOP EXPENSES =================
with tabs[3]:
    st.subheader("💸 Shop Daily Expenses")
    e_date = st.date_input("Expense Date", datetime.now(), key="e_date")
    e_title = st.text_input("Expense Reason (e.g. Tea, Rent, Electricity)")
    e_amt = st.number_input("Expense Amount", min_value=0, key="e_amt")
    if st.button("Save Expense"):
        c.execute("INSERT INTO expenses VALUES(?,?,?)", (e_date.strftime("%Y-%m-%d"), e_title, e_amt))
        conn.commit()
        st.success("Expense Recorded!")

# ================= 5. CAPITAL ACCOUNT =================
with tabs[4]:
    st.subheader("🤝 Partners Capital (Investment)")
    cap_date = st.date_input("Date", datetime.now(), key="cap_date")
    p_name = st.selectbox("Partner Name", ["M Waqas", "Farid Khan", "Farman Ali"])
    cap_type = st.selectbox("Action", ["Investment (Paise Lagaye)", "Withdrawal (Paise Nikale)"])
    cap_amt = st.number_input("Amount", min_value=0, key="cap_amt")
    if st.button("Update Capital"):
        c.execute("INSERT INTO partner_ledger VALUES(?,?,?,?,?)", (cap_date.strftime("%Y-%m-%d"), p_name, cap_type, cap_amt, "Capital Update"))
        conn.commit()
        st.success("Capital Account Updated!")

# ================= 6. REPORTS =================
with tabs[5]:
    st.subheader("📊 Business Overview")
    sales = pd.read_sql("SELECT SUM(total) FROM invoices", conn).iloc[0,0] or 0
    expenses = pd.read_sql("SELECT SUM(amount) FROM expenses", conn).iloc[0,0] or 0
    st.metric("Total Sales", f"Rs {sales}")
    st.metric("Total Shop Expenses", f"Rs {expenses}")
    st.metric("Net Profit", f"Rs {sales - expenses}")
