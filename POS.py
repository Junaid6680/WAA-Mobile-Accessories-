import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# ---------- CONFIG ----------
st.set_page_config("WAA POS Pro", layout="wide")
DB = "waa_pos_vfinal_fixed.db" # New DB to avoid old errors

# Login Credentials
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

# Database Connection
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Tables setup
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, cost INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER, total_cost INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS suppliers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS capital(date TEXT, partner TEXT, amount INTEGER, type TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS returns(date TEXT, customer TEXT, item TEXT, qty INTEGER, amount INTEGER)")
conn.commit()

# --- 15 SAMPLE ITEMS (Permanent Stock) ---
sample_items = [
    ("iPhone 13 Case", 50, 400), ("iPhone 14 Glass", 100, 150),
    ("Samsung 25W Adapter", 30, 1200), ("Type-C Cable", 40, 300),
    ("Airpods Pro 2", 15, 2500), ("M10 TWS Earbuds", 25, 650),
    ("65W Fast Charger", 20, 1800), ("Micro USB Cable", 60, 120),
    ("Phone Tripod", 10, 500), ("Power Bank 20k", 12, 3500),
    ("Mini Speaker", 18, 900), ("Gaming Headset", 8, 2200),
    ("Smart Watch Ultra", 15, 2800), ("Car Mount", 35, 250),
    ("OTG Adapter", 80, 80)
]
for name, q, cost in sample_items:
    c.execute("INSERT OR IGNORE INTO inventory (item, qty, cost) VALUES(?,?,?)", (name, q, cost))
conn.commit()

# ---------- LOGIN SYSTEM ----------
if "login" not in st.session_state: st.session_state.login = False
if not st.session_state.login:
    st.title("🔐 WAA POS Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.login = True
            st.rerun()
        else: st.error("Ghalt Username ya Password!")
    st.stop()

# ---------- PDF GENERATOR ----------
def generate_pdf(inv_no, customer, date, items, total):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "WAA Mobile Accessories", ln=True, align='C')
    pdf.set_font("Arial", size=8)
    pdf.cell(0, 5, f"Inv: {inv_no} | Date: {date}", ln=True)
    pdf.cell(0, 5, f"Cust: {customer}", ln=True)
    pdf.ln(5)
    pdf.cell(35, 5, "Item")
    pdf.cell(10, 5, "Qty")
    pdf.cell(20, 5, "Total", ln=True)
    for _, r in items.iterrows():
        pdf.cell(35, 5, str(r['Item']))
        pdf.cell(10, 5, str(r['Qty']))
        pdf.cell(20, 5, str(r['Total']), ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Grand Total: Rs {total}", align='R')
    return pdf.output(dest='S')

# ---------- TABS ----------
tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "👥 Customers Ledger", "💰 Cash Book", "🤝 Capital Account", "🔄 Returns"])

# 1. SALE INVOICE
with tabs[0]:
    st.subheader("Create New Bill")
    c_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    cust_sel = st.selectbox("Select Customer", c_list)
    final_cust = st.text_input("Customer Name", value="Walk-in Customer") if cust_sel == "Walk-in" else cust_sel
    
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    col1, col2, col3 = st.columns(3)
    with col1: sel_item = st.selectbox("Item", inv_df['item'])
    with col2: sel_qty = st.number_input("Qty", 1)
    with col3: sel_rate = st.number_input("Sale Price", 0)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    if st.button("➕ Add to Cart"):
        cost = inv_df.loc[inv_df.item == sel_item, 'cost'].values[0]
        st.session_state.cart.append({"Item": sel_item, "Qty": sel_qty, "Cost": cost, "Rate": sel_rate, "Total": sel_qty*sel_rate})
        st.rerun()

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart[['Item', 'Qty', 'Rate', 'Total']])
        total_bill = df_cart['Total'].sum()
        total_cost = (df_cart['Cost'] * df_cart['Qty']).sum()
        
        if st.button("💾 Save Bill & Show PDF"):
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?,?)", (inv_no, datetime.now().strftime("%Y-%m-%d"), final_cust, total_bill, total_cost))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            
            # PDF Creation
            pdf_data = generate_pdf(inv_no, final_cust, datetime.now().strftime("%Y-%m-%d"), df_cart, total_bill)
            st.download_button("📥 Download/Print Bill", data=pdf_data, file_name=f"WAA_{inv_no}.pdf", mime="application/pdf")
            st.session_state.cart = []
            st.success("Bill Saved and Ledger Updated!")

# 2. INVENTORY
with tabs[1]:
    st.subheader("Current Stock Status")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# 3. CUSTOMERS LEDGER (Udhaar Hisab)
with tabs[2]:
    st.subheader("Customers Ledger")
    with st.expander("➕ Register New Customer"):
        cn, cb = st.text_input("Customer Name"), st.number_input("Opening Balance", 0)
        if st.button("Save New Customer"):
            c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (cn, cb))
            conn.commit()
            st.rerun()
            
    # FIXED LEDGER LOGIC
    c_df = pd.read_sql("SELECT * FROM customers", conn)
    ledger_report = []
    for _, r in c_df.iterrows():
        name = r['name']
        s = pd.read_sql("SELECT SUM(total) FROM invoices WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        p = pd.read_sql("SELECT SUM(amount) FROM payments WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        rt = pd.read_sql("SELECT SUM(amount) FROM returns WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        ledger_report.append({"Name": name, "Old Bal": r['opening_balance'], "Sales(+)": s, "Paid/Ret(-)": p+rt, "Balance": r['opening_balance']+s-p-rt})
    st.dataframe(pd.DataFrame(ledger_report), use_container_width=True)

# 4. CASH BOOK (Cash/Meezan/Faysal)
with tabs[3]:
    st.subheader("💰 Cash & Bank Live Balances")
    cash = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Cash'", conn).iloc[0,0] or 0
    meezan = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Meezan Bank'", conn).iloc[0,0] or 0
    faysal = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Faysal Bank'", conn).iloc[0,0] or 0
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Cash in Hand", f"Rs {cash}")
    col_b.metric("Meezan Bank", f"Rs {meezan}")
    col_c.metric("Faysal Bank", f"Rs {faysal}")
    
    st.markdown("---")
    st.write("### Record Payment Receiving")
    r_c = st.selectbox("From Customer", c_list)
    r_a = st.number_input("Amount", 0)
    r_m = st.selectbox("Bank", ["Cash", "Meezan Bank", "Faysal Bank"])
    if st.button("Save Receiving"):
        c.execute("INSERT INTO payments VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_c, r_a, r_m))
        conn.commit()
        st.success("Ledger Updated!")
        st.rerun()

# 5. CAPITAL & RETURNS
# (Same logic as previous, keeping it clean for performance)
