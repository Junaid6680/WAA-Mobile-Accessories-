# =================================================
# WAA MOBILE ACCESSORIES – FINAL MULTI-ITEM POS
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
DB = "waa_multi_pos.db"

# ---------- DATABASE ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS inventory(
item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)""")

c.execute("""CREATE TABLE IF NOT EXISTS invoices(
inv_no INTEGER, date TEXT, customer TEXT,
total INTEGER, paid INTEGER, balance INTEGER)""")

c.execute("""CREATE TABLE IF NOT EXISTS invoice_items(
inv_no INTEGER, item TEXT, qty INTEGER, price INTEGER, total INTEGER)""")

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

# ---------- SESSION CART ----------
if "cart" not in st.session_state:
    st.session_state.cart = []

# ---------- INVOICE NO ----------
last = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0]
INV_NO = 1001 if last is None else last + 1

tab1, tab2, tab3 = st.tabs(["🧾 Invoice", "📦 Inventory", "📊 Reports"])

# ================= INVOICE =================
with tab1:
    st.subheader("Multi-Item Invoice")

    customer = st.text_input("Customer Name")

    inv = pd.read_sql("SELECT * FROM inventory", conn)

    if not inv.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            item = st.selectbox("Item", inv["item"])
        with col2:
            qty = st.number_input("Qty", 1)
        with col3:
            price = inv.loc[inv.item == item, "price"].values[0]

        if st.button("➕ Add Item"):
            stock = inv.loc[inv.item == item, "qty"].values[0]
            if qty > stock:
                st.error("Stock not available")
            else:
                st.session_state.cart.append({
                    "item": item,
                    "qty": qty,
                    "price": price,
                    "total": qty * price
                })

    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df, use_container_width=True)

        grand_total = cart_df["total"].sum()
        st.metric("Invoice Total", f"Rs {grand_total}")

        paid = st.number_input("Paid Amount", 0)
        balance = grand_total - paid

        if st.button("💾 Save & Print Invoice"):
            if customer == "":
                st.error("Customer required")
            else:
                c.execute("INSERT INTO invoices VALUES(?,?,?,?,?,?)",
                (INV_NO, datetime.now(), customer, grand_total, paid, balance))

                for row in st.session_state.cart:
                    c.execute("INSERT INTO invoice_items VALUES(?,?,?,?,?)",
                    (INV_NO, row["item"], row["qty"], row["price"], row["total"]))
                    c.execute("UPDATE inventory SET qty=qty-? WHERE item=?",
                    (row["qty"], row["item"]))

                conn.commit()

                # ---------- PDF ----------
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
                for r in st.session_state.cart:
                    pdf.cell(60,8,r["item"],1)
                    pdf.cell(20,8,str(r["qty"]),1)
                    pdf.cell(30,8,str(r["price"]),1)
                    pdf.cell(30,8,str(r["total"]),1,ln=True)

                pdf.ln(3)
                pdf.cell(0,8,f"Grand Total: Rs {grand_total}",ln=True)
                pdf.cell(0,8,f"Paid: Rs {paid}",ln=True)
                pdf.cell(0,8,f"Balance: Rs {balance}",ln=True)

                os.makedirs("invoices", exist_ok=True)
                file = f"invoices/Invoice_{INV_NO}.pdf"
                pdf.output(file)

                st.success("Invoice Created")
                st.download_button("⬇ Download Invoice", open(file,"rb"),
                                   file_name=f"Invoice_{INV_NO}.pdf")

                st.session_state.cart = []

# ================= INVENTORY =================
with tab2:
    st.subheader("Inventory")

    n = st.text_input("Item Name")
    q = st.number_input("Opening Qty", 0)
    p = st.number_input("Sale Price", 0)

    if st.button("Save Item") and n != "":
        c.execute("INSERT OR REPLACE INTO inventory VALUES(?,?,?)",(n,q,p))
        conn.commit()

    st.dataframe(pd.read_sql("SELECT * FROM inventory",conn), use_container_width=True)

# ================= REPORT =================
with tab3:
    st.subheader("Invoices / Sales Report")
    inv_df = pd.read_sql("SELECT * FROM invoices", conn)
    st.dataframe(inv_df, use_container_width=True)
