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
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT)") # New Table for Receiving
c.execute("CREATE TABLE IF NOT EXISTS expenses(date TEXT, title TEXT, amount INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS partner_ledger(date TEXT, partner_name TEXT, type TEXT, amount INTEGER, remarks TEXT)")
conn.commit()

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

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "📝 Khata & Receiving", "💸 Shop Expenses", "🤝 Capital Account", "📊 Business Reports"])

# ================= 1. SALE INVOICE (With Cart Edit Option) =================
with tabs[0]:
    st.subheader("New Sale")
    col_a, col_b = st.columns(2)
    with col_a: sale_date = st.date_input("Invoice Date", datetime.now())
    with col_b: customer_name = st.text_input("Customer Name", value="Walk-in")
    
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    c1, c2 = st.columns(2)
    with c1: item = st.selectbox("Select Item", inv_df["item"]) if not inv_df.empty else None
    with c2: qty = st.number_input("Qty", min_value=1, value=1)
    
    if "cart_sale" not in st.session_state: st.session_state.cart_sale = []

    if st.button("➕ Add to Cart"):
        price = inv_df.loc[inv_df.item==item, "price"].values[0]
        st.session_state.cart_sale.append({"item": item, "qty": qty, "price": price, "total": qty*price})
    
    if st.session_state.cart_sale:
        df_cart = pd.DataFrame(st.session_state.cart_sale)
        st.table(df_cart)
        
        # --- Edit Option: Clear Cart if customer changes mind ---
        if st.button("❌ Clear Cart (Bill Edit)"):
            st.session_state.cart_sale = []
            st.rerun()

        if st.button("💾 Finalize & Print Bill"):
            last_no = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000
            new_no = last_no + 1
            total_bill = sum(x['total'] for x in st.session_state.cart_sale)
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (new_no, sale_date.strftime("%Y-%m-%d"), customer_name, total_bill))
            for r in st.session_state.cart_sale:
                c.execute("UPDATE inventory SET qty=qty-? WHERE item=?", (r['qty'], r['item']))
            conn.commit()
            st.session_state.cart_sale = []
            st.success(f"Bill #{new_no} Saved!")
            st.rerun()

# ================= 2. INVENTORY (Return/Stock Adjustment) =================
with tabs[1]:
    st.subheader("📦 Stock Management")
    st.write("Agar customer item wapis kare to yahan se Qty barha dein.")
    edit_item = st.selectbox("Select Item to Adjust", inv_df["item"]) if not inv_df.empty else None
    add_qty = st.number_input("Adjust Qty (+ for Return, - for Damage)", value=0)
    if st.button("Update Stock"):
        c.execute("UPDATE inventory SET qty=qty+? WHERE item=?", (add_qty, edit_item))
        conn.commit()
        st.success("Stock Adjusted!")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# ================= 3. KHATA & RECEIVING (Bank/Cash Payments) =================
with tabs[2]:
    st.subheader("💰 Customer Payments (Receiving)")
    st.write("Purani payment receive karne ke liye yahan entry karein.")
    
    col1, col2, col3 = st.columns(3)
    with col1: rec_date = st.date_input("Receiving Date", datetime.now())
    with col2: rec_cust = st.text_input("Customer Name (for Payment)")
    with col3: rec_amt = st.number_input("Amount Received", min_value=0)
    
    rec_method = st.selectbox("Payment Method", ["Bank Transfer", "Cash", "EasyPaisa/JazzCash"])
    
    if st.button("📥 Record Receiving"):
        c.execute("INSERT INTO payments VALUES(?,?,?,?)", (rec_date.strftime("%Y-%m-%d"), rec_cust, rec_amt, rec_method))
        conn.commit()
        st.success(f"Rs. {rec_amt} received from {rec_cust} via {rec_method}")

    st.markdown("---")
    st.subheader("📊 Khata Summary (Total Sale vs Total Received)")
    sales_data = pd.read_sql("SELECT customer, SUM(total) as Total_Bill FROM invoices GROUP BY customer", conn)
    pay_data = pd.read_sql("SELECT customer, SUM(amount) as Paid_Amount FROM payments GROUP BY customer", conn)
    
    if not sales_data.empty:
        summary = pd.merge(sales_data, pay_data, on="customer", how="left").fillna(0)
        summary['Remaining_Balance'] = summary['Total_Bill'] - summary['Paid_Amount']
        st.dataframe(summary, use_container_width=True)

# ================= REST OF THE CODE (Expenses, Capital, Reports) =================
# ... (Baqi code pehle wala hi rahe ga)
