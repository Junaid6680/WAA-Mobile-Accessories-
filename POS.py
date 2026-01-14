import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# ---------- CONFIG ----------
st.set_page_config("WAA POS", layout="wide")
DB = "waa_pos_store.db"

# Login Credentials
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

# Database Connection
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Tables setup
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
conn.commit()

# ---------- LOGIN SYSTEM ----------
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

# ---------- APP LAYOUT ----------
st.sidebar.title("WAA Mobile")
if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

st.title("🏬 WAA Mobile Accessories")
st.markdown("---")

# ---------- PDF GENERATOR ----------
def generate_bill_pdf(inv_no, customer, date, items_df, total):
    pdf = FPDF(format=(80, 150)) # Thermal Printer Size
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 5, "WAA Mobile Accessories", ln=True, align='C')
    pdf.set_font("Arial", size=8)
    pdf.cell(0, 5, f"Bill #: {inv_no} | Date: {date}", ln=True, align='C')
    pdf.cell(0, 5, f"Customer: {customer}", ln=True, align='C')
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(35, 5, "Item")
    pdf.cell(10, 5, "Qty")
    pdf.cell(20, 5, "Total", ln=True)
    pdf.set_font("Arial", size=8)
    for _, row in items_df.iterrows():
        pdf.cell(35, 5, str(row['Item']))
        pdf.cell(10, 5, str(row['Qty']))
        pdf.cell(20, 5, str(row['Total']), ln=True)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Grand Total: Rs {total}", ln=True, align='R')
    return pdf.output(dest='S')

# ---------- TABS ----------
tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory Management", "👥 Customers & Khata", "💰 Receiving"])

# 1. SALE INVOICE
with tabs[0]:
    st.subheader("Create Bill")
    c_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    cust_sel = st.selectbox("Select Customer", c_list)
    final_cust = st.text_input("Customer Name", value="Walk-in Customer") if cust_sel == "Walk-in" else cust_sel
    
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    col1, col2 = st.columns(2)
    with col1: 
        sel_item = st.selectbox("Select Item", inv_df['item']) if not inv_df.empty else None
    with col2:
        sel_qty = st.number_input("Quantity", min_value=1, value=1)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    if st.button("➕ Add to Cart"):
        if sel_item:
            p = inv_df.loc[inv_df.item == sel_item, 'price'].values[0]
            st.session_state.cart.append({"Item": sel_item, "Qty": sel_qty, "Price": p, "Total": sel_qty*p})
            st.rerun()

    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.table(cart_df)
        total_bill = cart_df['Total'].sum()
        st.write(f"### Total: Rs {total_bill}")
        
        if st.button("💾 Finalize & Download PDF"):
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (inv_no, datetime.now().strftime("%Y-%m-%d"), final_cust, total_bill))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            
            pdf_data = generate_bill_pdf(inv_no, final_cust, datetime.now().strftime("%Y-%m-%d"), cart_df, total_bill)
            st.download_button("📥 Download PDF Bill", data=pdf_data, file_name=f"WAA_Bill_{inv_no}.pdf", mime="application/pdf")
            st.session_state.cart = []
            st.success("Sale Recorded!")

# 2. INVENTORY MANAGEMENT
with tabs[1]:
    st.subheader("Manage Items & Stock")
    with st.expander("➕ Add/Purchase New Stock"):
        n_item = st.text_input("Item Name")
        n_qty = st.number_input("Quantity to Add", min_value=0)
        n_prc = st.number_input("Selling Price", min_value=0)
        if st.button("Save Stock"):
            c.execute("INSERT OR REPLACE INTO inventory (item, qty, price) VALUES (?, COALESCE((SELECT qty FROM inventory WHERE item=?) + ?, ?), ?)", 
                      (n_item, n_item, n_qty, n_qty, n_prc))
            conn.commit()
            st.success(f"{n_item} Updated!")
            st.rerun()
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# 3. CUSTOMERS & KHATA
with tabs[2]:
    st.subheader("Customer Ledger")
    with st.expander("➕ Add New Permanent Customer"):
        cn = st.text_input("Full Name")
        cb = st.number_input("Opening Balance", min_value=0)
        if st.button("Register Customer"):
            c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (cn, cb))
            conn.commit()
            st.rerun()
            
    all_c = pd.read_sql("SELECT * FROM customers", conn)
    ledger = []
    for _, r in all_c.iterrows():
        name = r['name']
        op = r['opening_balance']
        sales = pd.read_sql(f"SELECT SUM(total) FROM invoices WHERE customer='{name}'", conn).iloc[0,0] or 0
        paid = pd.read_sql(f"SELECT SUM(amount) FROM payments WHERE customer='{name}'", conn).iloc[0,0] or 0
        bal = op + sales - paid
        ledger.append({"Customer": name, "Old Bal": op, "Sales": sales, "Paid": paid, "Total Payable": bal})
    st.table(pd.DataFrame(ledger))

# 4. RECEIVING
with tabs[3]:
    st.subheader("Receive Payment")
    names = [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    if names:
        r_c = st.selectbox("Select Customer", names)
        r_a = st.number_input("Amount Received", min_value=0)
        r_m = st.selectbox("Payment Method", ["Cash", "Bank Transfer", "EasyPaisa"])
        if st.button("Record Payment"):
            c.execute("INSERT INTO payments VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_c, r_a, r_m))
            conn.commit()
            st.success("Payment Received and Updated in Ledger!")
    else:
        st.info("Pehle customer register karein.")
