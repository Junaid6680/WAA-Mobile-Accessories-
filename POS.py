# ==============================
# WAA Mobile Accessories - FINAL POS
# Streamlit + SQLite
# ==============================

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import os

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="WAA Mobile Accessories POS", layout="wide")

SHOP_NAME = "WAA Mobile Accessories"
SHOP_ADDRESS = "Shop No T27, Hassan Center 2, Hall Road Lahore"
SHOP_CONTACT = "M Waqas 0315-4899075 | Farid Khan 0328-4080860 | Farman Ali 0303-0075400"

DB_NAME = "waa_pos.db"

# ---------- DATABASE ----------
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    item TEXT PRIMARY KEY,
    stock INTEGER,
    price INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    bill_no INTEGER,
    date TEXT,
    customer TEXT,
    item TEXT,
    qty INTEGER,
    amount INTEGER,
    cash INTEGER,
    bank INTEGER,
    balance INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    date TEXT,
    description TEXT,
    amount INTEGER
)
""")
conn.commit()

# ---------- LOGIN ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == "admin" and pwd == "1234":
            st.session_state.logged_in = True
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid username or password")
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

# ---------- BILL NUMBER ----------
last_bill = cursor.execute("SELECT MAX(bill_no) FROM sales").fetchone()[0]
bill_no = 1001 if last_bill is None else last_bill + 1

# ---------- TABS ----------
tab1, tab2, tab3, tab4 = st.tabs([
    "🧾 Billing", "📦 Inventory", "📊 Reports", "💰 Profit & Backup"
])

# ================= BILLING =================
with tab1:
    st.subheader("Create Bill")

    customer = st.text_input("Customer Name")

    inv_df = pd.read_sql("SELECT * FROM inventory", conn)

    if inv_df.empty:
        st.warning("Inventory empty. Add items first.")
    else:
        item = st.selectbox("Select Item", inv_df["item"])
        qty = st.number_input("Quantity", min_value=1, value=1)

        price = inv_df.loc[inv_df["item"] == item, "price"].values[0]
        stock = inv_df.loc[inv_df["item"] == item, "stock"].values[0]

        total = price * qty
        st.metric("Bill Amount", f"Rs. {total}")

        cash = st.number_input("Cash Received", min_value=0)
        bank = st.number_input("Bank / JazzCash / EasyPaisa", min_value=0)
        balance = total - (cash + bank)

        st.write("🧾 Bill No:", bill_no)
        st.write("🗓 Date:", datetime.now().strftime("%d-%m-%Y %H:%M"))

        if st.button("Save & Print Bill"):
            if qty > stock:
                st.error("❌ Stock not available")
            elif customer.strip() == "":
                st.warning("Customer name required")
            else:
                cursor.execute(
                    "INSERT INTO sales VALUES (?,?,?,?,?,?,?,?,?)",
                    (bill_no, datetime.now().strftime("%Y-%m-%d %H:%M"),
                     customer, item, qty, total, cash, bank, balance)
                )

                cursor.execute(
                    "UPDATE inventory SET stock = stock - ? WHERE item = ?",
                    (qty, item)
                )
                conn.commit()

                # PDF Bill
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(0, 10, SHOP_NAME, ln=True, align="C")
                pdf.cell(0, 8, SHOP_ADDRESS, ln=True, align="C")
                pdf.cell(0, 8, SHOP_CONTACT, ln=True, align="C")
                pdf.ln(5)
                pdf.cell(0, 8, f"Bill No: {bill_no}", ln=True)
                pdf.cell(0, 8, f"Customer: {customer}", ln=True)
                pdf.cell(0, 8, f"Item: {item}", ln=True)
                pdf.cell(0, 8, f"Qty: {qty}", ln=True)
                pdf.cell(0, 8, f"Total: Rs. {total}", ln=True)
                pdf.cell(0, 8, f"Paid: Rs. {cash + bank}", ln=True)
                pdf.cell(0, 8, f"Balance: Rs. {balance}", ln=True)

                if not os.path.exists("bills"):
                    os.mkdir("bills")

                path = f"bills/Bill_{bill_no}.pdf"
                pdf.output(path)

                st.success("Bill saved successfully")
                st.download_button(
                    "⬇ Download Bill PDF",
                    open(path, "rb"),
                    file_name=f"Bill_{bill_no}.pdf"
                )

# ================= INVENTORY =================
with tab2:
    st.subheader("Inventory Management")

    name = st.text_input("Item Name")
    qty = st.number_input("Quantity", min_value=0)
    price = st.number_input("Sale Price", min_value=0)

    if st.button("Add / Update Item"):
        cursor.execute("SELECT * FROM inventory WHERE item=?", (name,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE inventory SET stock = stock + ?, price=? WHERE item=?",
                (qty, price, name)
            )
        else:
            cursor.execute(
                "INSERT INTO inventory VALUES (?,?,?)",
                (name, qty, price)
            )
        conn.commit()
        st.success("Inventory updated")

    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# ================= REPORTS =================
with tab3:
    st.subheader("Sales Report")
    sales_df = pd.read_sql("SELECT * FROM sales", conn)
    st.dataframe(sales_df, use_container_width=True)

    if not sales_df.empty:
        csv = sales_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Excel Report", csv, "sales_report.csv")

# ================= PROFIT & BACKUP =================
with tab4:
    st.subheader("Expense Entry")

    desc = st.text_input("Expense Description")
    amt = st.number_input("Expense Amount", min_value=0)

    if st.button("Add Expense"):
        cursor.execute(
            "INSERT INTO expenses VALUES (?,?,?)",
            (datetime.now().strftime("%Y-%m-%d"), desc, amt)
        )
        conn.commit()
        st.success("Expense added")

    exp_df = pd.read_sql("SELECT * FROM expenses", conn)

    total_sales = sales_df["amount"].sum() if not sales_df.empty else 0
    total_exp = exp_df["amount"].sum() if not exp_df.empty else 0
    profit = total_sales - total_exp

    st.metric("Total Sales", f"Rs. {total_sales}")
    st.metric("Total Expense", f"Rs. {total_exp}")
    st.metric("Net Profit", f"Rs. {profit}")

    st.subheader("Full Database Backup")
    with open(DB_NAME, "rb") as f:
        st.download_button("⬇ Download Backup", f, "waa_pos_backup.db")
