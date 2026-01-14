import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# ---------- CONFIG ----------
st.set_page_config("WAA POS Pro", layout="wide")
DB = "waa_pos_vfinal.db"

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
c.execute("CREATE TABLE IF NOT EXISTS supplier_payments(date TEXT, supplier TEXT, amount INTEGER, method TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS capital(date TEXT, partner TEXT, amount INTEGER, type TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS returns(date TEXT, customer TEXT, item TEXT, qty INTEGER, amount INTEGER)")
conn.commit()

# --- 15 SAMPLE ITEMS (Automatic Add) ---
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

# ---------- APP LAYOUT ----------
st.sidebar.title("WAA Mobile")
if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "👥 Customers Ledger", "🚛 Suppliers Khata", "💰 Cash Book", "🤝 Capital Account", "🔄 Returns"])

# ================= 1. SALE INVOICE =================
with tabs[0]:
    st.subheader("New Sale Invoice")
    c_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    cust_sel = st.selectbox("Select Customer", c_list)
    final_cust = st.text_input("Customer Name", value="Walk-in Customer") if cust_sel == "Walk-in" else cust_sel
    
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    col1, col2, col3 = st.columns(3)
    with col1: sel_item = st.selectbox("Select Item", inv_df['item']) if not inv_df.empty else None
    with col2: sel_qty = st.number_input("Quantity", min_value=1, value=1)
    with col3: sel_rate = st.number_input("Sale Rate (Unit Price)", min_value=0)
    
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
        st.write(f"### Grand Total: Rs {total_bill}")
        
        if st.button("💾 Finalize Bill"):
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?,?)", (inv_no, datetime.now().strftime("%Y-%m-%d"), final_cust, total_bill, total_cost))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            st.session_state.cart = []
            st.success("Bill Saved & Stock Updated!")
            st.rerun()

# ================= 2. CUSTOMERS LEDGER =================
with tabs[2]:
    st.subheader("👥 Customer Ledger (Udhaar Hisab)")
    with st.expander("Register New Permanent Customer"):
        cn, cb = st.text_input("Customer Name"), st.number_input("Opening Balance (Pichla Udhaar)", 0)
        if st.button("Save Customer"):
            c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (cn, cb))
            conn.commit()
            st.rerun()
    
    # Live Calculation for Ledger
    cust_df = pd.read_sql("SELECT * FROM customers", conn)
    ledger_data = []
    for _, r in cust_df.iterrows():
        name = r['name']
        sales = pd.read_sql("SELECT SUM(total) FROM invoices WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        rets = pd.read_sql("SELECT SUM(amount) FROM returns WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        paid = pd.read_sql("SELECT SUM(amount) FROM payments WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        balance = r['opening_balance'] + sales - rets - paid
        ledger_data.append({"Customer": name, "Old Bal": r['opening_balance'], "Sales(+)": sales, "Paid/Returns(-)": paid+rets, "Net Balance": balance})
    st.dataframe(pd.DataFrame(ledger_data), use_container_width=True)

# ================= 3. SUPPLIERS =================
with tabs[3]:
    st.subheader("🚛 Supplier Khata")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        s_name = st.text_input("Supplier Name")
        s_ob = st.number_input("Supplier Opening Balance", 0)
        if st.button("Add Supplier"):
            c.execute("INSERT OR IGNORE INTO suppliers VALUES(?,?)", (s_name, s_ob))
            conn.commit()
            st.rerun()
    with col_s2:
        st.dataframe(pd.read_sql("SELECT * FROM suppliers", conn), use_container_width=True)

# ================= 4. CASH BOOK =================
with tabs[4]:
    st.subheader("💰 Cash & Bank Live Balance")
    cash_in = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Cash'", conn).iloc[0,0] or 0
    meezan = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Meezan Bank'", conn).iloc[0,0] or 0
    faysal = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Faysal Bank'", conn).iloc[0,0] or 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("💵 Cash in Hand", f"Rs {cash_in}")
    c2.metric("🏦 Meezan Bank", f"Rs {meezan}")
    c3.metric("🏦 Faysal Bank", f"Rs {faysal}")
    
    st.markdown("---")
    st.subheader("📥 Receive Payment from Customer")
    r_cust = st.selectbox("From Customer", c_list, key="rec_cust")
    r_amt = st.number_input("Amount Received", 0, key="rec_amt")
    r_meth = st.selectbox("Bank/Method", ["Cash", "Meezan Bank", "Faysal Bank", "EasyPaisa"], key="rec_meth")
    if st.button("Record Receiving"):
        c.execute("INSERT INTO payments VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_cust, r_amt, r_meth))
        conn.commit()
        st.success(f"Received Rs. {r_amt} from {r_cust}")
        st.rerun()

# ================= 5. CAPITAL ACCOUNT =================
with tabs[5]:
    st.subheader("🤝 Partner Capital Management")
    p_name = st.selectbox("Partner", ["M Waqas", "Farid Khan", "Farman Ali"])
    p_amt = st.number_input("Amount", 0, key="cap_amt")
    p_type = st.selectbox("Type", ["Investment (In)", "Withdrawal (Out)"])
    if st.button("Save Capital Entry"):
        c.execute("INSERT INTO capital VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), p_name, p_amt, p_type))
        conn.commit()
        st.success("Capital Account Updated!")
    
    st.write("### Summary")
    for p in ["M Waqas", "Farid Khan", "Farman Ali"]:
        inv = pd.read_sql(f"SELECT SUM(amount) FROM capital WHERE partner='{p}' AND type LIKE 'Investment%'", conn).iloc[0,0] or 0
        wth = pd.read_sql(f"SELECT SUM(amount) FROM capital WHERE partner='{p}' AND type LIKE 'Withdrawal%'", conn).iloc[0,0] or 0
        st.info(f"**{p}**: Net Capital: Rs. {inv - wth}")

# ================= 6. RETURNS =================
with tabs[6]:
    st.subheader("🔄 Return Item Management")
    ret_c = st.selectbox("Customer ", ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()], key="ret_cust")
    ret_i = st.selectbox("Item Name ", [r[0] for r in c.execute("SELECT item FROM inventory").fetchall()], key="ret_item")
    ret_q = st.number_input("Return Qty", 1, key="ret_qty")
    ret_v = st.number_input("Return Value (Amount)", 0, key="ret_val")
    if st.button("Process Return"):
        c.execute("INSERT INTO returns VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), ret_c, ret_i, ret_q, ret_v))
        c.execute("UPDATE inventory SET qty = qty + ? WHERE item = ?", (ret_q, ret_i))
        conn.commit()
        st.success("Return processed! Stock and Ledger updated.")
        st.rerun()
