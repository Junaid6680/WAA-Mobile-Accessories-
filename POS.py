import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# ---------- CONFIG ----------
st.set_page_config("WAA POS Pro", layout="wide")
DB = "waa_pos_v7_final.db" # Naye database ke sath start karein

conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# ---------- DATABASE TABLES ----------
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, cost INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER, total_cost INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS suppliers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS supplier_payments(date TEXT, supplier TEXT, amount INTEGER, method TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS capital(date TEXT, partner TEXT, amount INTEGER, type TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS returns(date TEXT, customer TEXT, item TEXT, qty INTEGER, amount INTEGER)")
conn.commit()

# --- 15 SAMPLE ITEMS ---
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
        if u == "admin" and p == "1234":
            st.session_state.login = True
            st.rerun()
        else: st.error("Ghalt Username ya Password!")
    st.stop()

# ---------- APP LAYOUT ----------
st.sidebar.title("WAA Mobile")
if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "👥 Customers Ledger", "🚛 Suppliers Khata", "💰 Cash Book", "🤝 Capital Account", "🔄 Returns", "📊 Reports"])

# 1. SALE INVOICE
with tabs[0]:
    st.subheader("New Sale")
    c_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    cust_sel = st.selectbox("Select Customer", c_list)
    
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    col1, col2, col3 = st.columns(3)
    with col1: sel_item = st.selectbox("Item", inv_df['item'])
    with col2: sel_qty = st.number_input("Quantity", 1)
    with col3: sel_rate = st.number_input("Rate (Aap Likhein)", 0)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    if st.button("➕ Add to Cart"):
        cost = inv_df.loc[inv_df.item == sel_item, 'cost'].values[0]
        st.session_state.cart.append({"Item": sel_item, "Qty": sel_qty, "Cost": cost, "Rate": sel_rate, "Total": sel_qty*sel_rate})
        st.rerun()

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart[['Item', 'Qty', 'Rate', 'Total']])
        total_bill = df_cart['Total'].sum()
        st.markdown(f"### 🏷️ Total Amount: Rs {total_bill}")
        
        if st.button("💾 Finalize Bill"):
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            total_cost = (df_cart['Cost'] * df_cart['Qty']).sum()
            c.execute("INSERT INTO invoices VALUES(?,?,?,?,?)", (inv_no, datetime.now().strftime("%Y-%m-%d"), cust_sel, total_bill, total_cost))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            st.session_state.cart = []
            st.success("Bill Saved! Customer Ledger Updated.")
            st.rerun()

# 2. INVENTORY
with tabs[1]:
    st.subheader("Current Stock Status")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# 3. CUSTOMERS LEDGER
with tabs[2]:
    st.subheader("Customer Udhaar Ledger")
    with st.expander("Register New Customer"):
        cn, cb = st.text_input("Customer Name"), st.number_input("Opening Bal", 0)
        if st.button("Add Cust"): 
            c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (cn, cb)); conn.commit(); st.rerun()
    
    c_df = pd.read_sql("SELECT * FROM customers", conn)
    l_data = []
    for _, r in c_df.iterrows():
        name = r['name']
        s = pd.read_sql("SELECT SUM(total) FROM invoices WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        p = pd.read_sql("SELECT SUM(amount) FROM payments WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        rt = pd.read_sql("SELECT SUM(amount) FROM returns WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        l_data.append({"Name": name, "Old Bal": r['opening_balance'], "Sales(+)": s, "Paid/Ret(-)": p+rt, "Payable": r['opening_balance']+s-p-rt})
    st.table(pd.DataFrame(l_data))

# 4. SUPPLIERS KHATA (Added Missing Tab)
with tabs[3]:
    st.subheader("Suppliers Khata")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        s_name = st.text_input("Supplier Name")
        s_bal = st.number_input("Supplier Opening Balance", 0)
        if st.button("Save Supplier"):
            c.execute("INSERT OR IGNORE INTO suppliers VALUES(?,?)", (s_name, s_bal))
            conn.commit(); st.rerun()
    with col_s2:
        st.write("Current Suppliers:")
        st.dataframe(pd.read_sql("SELECT * FROM suppliers", conn))

# 5. CASH BOOK
with tabs[4]:
    st.subheader("💰 Live Balance")
    cash = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Cash'", conn).iloc[0,0] or 0
    meezan = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Meezan Bank'", conn).iloc[0,0] or 0
    faysal = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Faysal Bank'", conn).iloc[0,0] or 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Cash", f"Rs {cash}"); c2.metric("Meezan", f"Rs {meezan}"); c3.metric("Faysal", f"Rs {faysal}")
    
    st.divider()
    st.write("### Record Payment Receiving")
    r_cust = st.selectbox("From Customer", c_list)
    r_amt = st.number_input("Amount Received", 0)
    r_meth = st.selectbox("Receive in", ["Cash", "Meezan Bank", "Faysal Bank"])
    if st.button("Save Payment"):
        c.execute("INSERT INTO payments VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_cust, r_amt, r_meth))
        conn.commit(); st.success("Balance & Ledger Updated!"); st.rerun()

# 6. CAPITAL ACCOUNT
with tabs[5]:
    st.subheader("Partner Capital")
    p_name = st.selectbox("Partner", ["M Waqas", "Farid Khan", "Farman Ali"])
    p_amt = st.number_input("Amount ", 0)
    p_type = st.selectbox("Type ", ["Investment", "Withdrawal"])
    if st.button("Save Capital"):
        c.execute("INSERT INTO capital VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), p_name, p_amt, p_type))
        conn.commit(); st.success("Recorded!"); st.rerun()

# 7. RETURNS
with tabs[6]:
    st.subheader("Sales Return")
    ret_c = st.selectbox("Select Customer ", c_list, key="rtc")
    ret_i = st.selectbox("Select Item ", [r[0] for r in c.execute("SELECT item FROM inventory").fetchall()], key="rti")
    ret_q = st.number_input("Return Qty", 1)
    ret_v = st.number_input("Return Value", 0)
    if st.button("Process Return"):
        c.execute("INSERT INTO returns VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), ret_c, ret_i, ret_q, ret_v))
        c.execute("UPDATE inventory SET qty = qty + ? WHERE item = ?", (ret_q, ret_i))
        conn.commit(); st.success("Inventory & Ledger Adjusted!"); st.rerun()

# 8. REPORTS
with tabs[7]:
    st.subheader("📊 Business Overview")
    sales = pd.read_sql("SELECT SUM(total) FROM invoices", conn).iloc[0,0] or 0
    costs = pd.read_sql("SELECT SUM(total_cost) FROM invoices", conn).iloc[0,0] or 0
    st.info(f"**Total Sales:** Rs {sales} | **Net Profit:** Rs {sales - costs}")
