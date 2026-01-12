# =================================================
# WAA MOBILE ACCESSORIES – FULL ACCOUNTING POS
# Streamlit + SQLite
# =================================================

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

# ---------- DATABASE ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Inventory table
c.execute("""CREATE TABLE IF NOT EXISTS inventory(
item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)""")

# Sales invoice
c.execute("""CREATE TABLE IF NOT EXISTS invoices(
inv_no INTEGER, date TEXT, customer TEXT, total INTEGER, paid INTEGER, balance INTEGER)""")

# Multi-item invoice items
c.execute("""CREATE TABLE IF NOT EXISTS invoice_items(
inv_no INTEGER, item TEXT, qty INTEGER, price INTEGER, total INTEGER)""")

# Purchases
c.execute("""CREATE TABLE IF NOT EXISTS purchases(
pur_no INTEGER, date TEXT, supplier TEXT, total INTEGER, paid INTEGER, balance INTEGER)""")

c.execute("""CREATE TABLE IF NOT EXISTS purchase_items(
pur_no INTEGER, item TEXT, qty INTEGER, price INTEGER, total INTEGER)""")

# Payments ledger (cash/bank)
c.execute("""CREATE TABLE IF NOT EXISTS payments(
date TEXT, party TEXT, type TEXT, method TEXT, amount INTEGER)""")

# Expenses ledger
c.execute("""CREATE TABLE IF NOT EXISTS expenses(
date TEXT, title TEXT, amount INTEGER)""")

# Owner capital
c.execute("""CREATE TABLE IF NOT EXISTS capital(
date TEXT, type TEXT, amount INTEGER)""")

conn.commit()

# ---------- LOGIN ----------
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 POS Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Wrong login")
    st.stop()

# ---------- HEADER ----------
st.markdown(f"""
<h2 style='text-align:center'>{SHOP_NAME}</h2>
<p style='text-align:center'>
{SHOP_ADDRESS}<br>
📞 {SHOP_CONTACT}
</p>
<hr>
""", unsafe_allow_html=True)

# ---------- SESSION CARTS ----------
if "cart_sale" not in st.session_state:
    st.session_state.cart_sale = []
if "cart_purchase" not in st.session_state:
    st.session_state.cart_purchase = []

# ---------- INVOICE / PURCHASE NO ----------
last_inv = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0]
INV_NO = 1001 if last_inv is None else last_inv + 1
last_pur = c.execute("SELECT MAX(pur_no) FROM purchases").fetchone()[0]
PUR_NO = 1001 if last_pur is None else last_pur + 1

# ---------- TABS ----------
tabs = st.tabs(["🧾 Invoice", "📦 Inventory", "🏭 Purchases", "👤 Customers Ledger",
                "💰 Supplier Ledger", "💸 Cash/Bank & Expenses", "📊 Reports"])

# ================= SALE INVOICE =================
with tabs[0]:
    st.subheader("Multi-Item Sales Invoice")
    customer = st.text_input("Customer Name", key="cust_name")

    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    if not inv_df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            item = st.selectbox("Item", inv_df["item"], key="sale_item")
        with col2:
            qty = st.number_input("Qty", 1, min_value=1, key="sale_qty")
        with col3:
            price = inv_df.loc[inv_df.item==item, "price"].values[0]

        if st.button("➕ Add Item to Cart"):
            stock = inv_df.loc[inv_df.item==item, "qty"].values[0]
            if qty > stock:
                st.error("Stock not available")
            else:
                st.session_state.cart_sale.append({
                    "item": item,
                    "qty": qty,
                    "price": price,
                    "total": qty*price
                })

    if st.session_state.cart_sale:
        cart_df = pd.DataFrame(st.session_state.cart_sale)
        st.dataframe(cart_df, use_container_width=True)
        grand_total = cart_df["total"].sum()
        st.metric("Invoice Total", f"Rs {grand_total}")

        paid = st.number_input("Paid Amount", 0, min_value=0)
        balance = grand_total - paid

        if st.button("💾 Save & Print Invoice"):
            if customer.strip() == "":
                st.error("Customer required")
            else:
                c.execute("INSERT INTO invoices VALUES(?,?,?,?,?,?)",
                          (INV_NO, datetime.now(), customer, grand_total, paid, balance))
                for row in st.session_state.cart_sale:
                    c.execute("INSERT INTO invoice_items VALUES(?,?,?,?,?)",
                              (INV_NO, row["item"], row["qty"], row["price"], row["total"]))
                    c.execute("UPDATE inventory SET qty=qty-? WHERE item=?",
                              (row["qty"], row["item"]))
                # Record payment
                c.execute("INSERT INTO payments VALUES(?,?,?,?,?)",
                          (datetime.now(), customer, "Customer", "Cash/Bank", paid))
                conn.commit()

                # PDF invoice
                pdf = FPDF()
                pdf.add_page()
                if os.path.exists("logo.png"):
                    pdf.image("logo.png", 10, 8, 30)
                pdf.set_font("Arial","B",16)
                pdf.cell(0,10,SHOP_NAME,ln=True,align="C")
                pdf.set_font("Arial",size=11)
                pdf.cell(0,7,SHOP_ADDRESS,ln=True,align="C")
                pdf.cell(0,7,SHOP_CONTACT,ln=True,align="C")
                pdf.ln(5)
                pdf.set_font("Arial","B",12)
                pdf.cell(0,8,f"Invoice #: {INV_NO}",ln=True)
                pdf.cell(0,8,f"Customer: {customer}",ln=True)
                pdf.ln(3)
                pdf.set_font("Arial","B",10)
                pdf.cell(60,8,"Item",1)
                pdf.cell(20,8,"Qty",1)
                pdf.cell(30,8,"Price",1)
                pdf.cell(30,8,"Total",1,ln=True)
                pdf.set_font("Arial",size=10)
                for r in st.session_state.cart_sale:
                    pdf.cell(60,8,r["item"],1)
                    pdf.cell(20,8,str(r["qty"]),1)
                    pdf.cell(30,8,str(r["price"]),1)
                    pdf.cell(30,8,str(r["total"]),1,ln=True)
                pdf.ln(3)
                pdf.cell(0,8,f"Grand Total: Rs {grand_total}",ln=True)
                pdf.cell(0,8,f"Paid: Rs {paid}",ln=True)
                pdf.cell(0,8,f"Balance: Rs {balance}",ln=True)
                os.makedirs("invoices",exist_ok=True)
                file = f"invoices/Invoice_{INV_NO}.pdf"
                pdf.output(file)
                st.success("Invoice Created & Saved")
                st.download_button("⬇ Download Invoice", open(file,"rb"),file_name=f"Invoice_{INV_NO}.pdf")
                st.session_state.cart_sale = []

# ================= INVENTORY =================
with tabs[1]:
    st.subheader("Inventory Management")
    n = st.text_input("Item Name", key="inv_name")
    q = st.number_input("Qty", 0, key="inv_qty")
    p = st.number_input("Price", 0, key="inv_price")
    if st.button("Save / Update Item"):
        c.execute("INSERT OR REPLACE INTO inventory VALUES(?,?,?)",(n,q,p))
        conn.commit()
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# ================= PURCHASES =================
with tabs[2]:
    st.subheader("Supplier Purchases")
    supplier = st.text_input("Supplier Name", key="sup_name")
    item = st.text_input("Item Name", key="pur_item")
    qty = st.number_input("Qty", 1, min_value=1, key="pur_qty")
    price = st.number_input("Price per Item", 0, key="pur_price")
    total = qty*price
    paid = st.number_input("Paid Amount", 0, key="pur_paid")
    balance = total - paid
    if st.button("Save Purchase"):
        c.execute("INSERT INTO purchases VALUES(?,?,?,?,?,?)",
                  (PUR_NO, datetime.now(), supplier, total, paid, balance))
        c.execute("INSERT INTO purchase_items VALUES(?,?,?,?,?)",
                  (PUR_NO, item, qty, price, total))
        c.execute("INSERT OR IGNORE INTO inventory VALUES(?,?,?)",(item,0,price))
        c.execute("UPDATE inventory SET qty=qty+? WHERE item=?",(qty,item))
        c.execute("INSERT INTO payments VALUES(?,?,?,?,?)",
                  (datetime.now(), supplier, "Supplier", "Cash/Bank", paid))
        conn.commit()
        st.success("Purchase Recorded")

# ================= CUSTOMER LEDGER =================
with tabs[3]:
    st.subheader("Customer Ledger")
    df = pd.read_sql("""
        SELECT customer, SUM(total) as Sale, SUM(paid) as Paid, SUM(balance) as Balance
        FROM invoices GROUP BY customer
    """, conn)
    st.dataframe(df, use_container_width=True)

# ================= SUPPLIER LEDGER =================
with tabs[4]:
    st.subheader("Supplier Ledger")
    df = pd.read_sql("""
        SELECT supplier, SUM(total) as Purchase, SUM(paid) as Paid, SUM(balance) as Balance
        FROM purchases GROUP BY supplier
    """, conn)
    st.dataframe(df, use_container_width=True)

# ================= CASH / BANK / EXPENSES / CAPITAL =================
with tabs[5]:
    st.subheader("Cash / Bank & Expenses")
    st.write("💰 Record Owner Capital / Withdraw")
    cap_amt = st.number_input("Amount", 0)
    cap_type = st.selectbox("Type", ["Add","Withdraw"])
    if st.button("Save Capital"):
        c.execute("INSERT INTO capital VALUES(?,?,?)",(datetime.now(),cap_type,cap_amt))
        conn.commit()
        st.success("Saved")

    st.write("📌 Record Shop Expenses")
    exp_title = st.text_input("Expense Title")
    exp_amt = st.number_input("Expense Amount", 0)
    if st.button("Save Expense"):
        c.execute("INSERT INTO expenses VALUES(?,?,?)",(datetime.now(),exp_title,exp_amt))
        conn.commit()
        st.success("Saved")

    total_sales = pd.read_sql("SELECT SUM(total) FROM invoices", conn).iloc[0,0] or 0
    total_exp = pd.read_sql("SELECT SUM(amount) FROM expenses", conn).iloc[0,0] or 0
    capital_balance = pd.read_sql("""
        SELECT SUM(CASE WHEN type='Add' THEN amount ELSE -amount END) FROM capital
    """, conn).iloc[0,0] or 0

    st.metric("Total Sales", total_sales)
    st.metric("Total Expenses", total_exp)
    st.metric("Owner Capital Balance", capital_balance)
    st.metric("Net Profit", total_sales - total_exp)

# ================= REPORTS =================
with tabs[6]:
    st.subheader("Reports / Invoice History")
    df_inv = pd.read_sql("SELECT * FROM invoices", conn)
    st.dataframe(df_inv, use_container_width=True)
