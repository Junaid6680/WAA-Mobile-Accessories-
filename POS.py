import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# ---------- CONFIG ----------
st.set_page_config("WAA POS Pro", layout="wide")
DB = "waa_pos_store_v2.db"

# Login Credentials
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

# Database Connection
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Tables setup
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, cost INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER, profit INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS capital(date TEXT, partner TEXT, amount INTEGER, type TEXT)") # Investment/Withdrawal
c.execute("CREATE TABLE IF NOT EXISTS returns(date TEXT, customer TEXT, item TEXT, qty INTEGER, amount INTEGER)")
conn.commit()

# --- 15 SAMPLE ITEMS AUTOMATIC ADD ---
sample_items = [
    ("iPhone 13 Case", 50, 400, 850), ("iPhone 14 Glass", 100, 150, 450),
    ("Samsung 25W Adapter", 30, 1200, 2200), ("Type-C Cable", 40, 300, 950),
    ("Airpods Pro 2", 15, 2500, 4800), ("M10 TWS Earbuds", 25, 650, 1250),
    ("65W Fast Charger", 20, 1800, 3200), ("Micro USB Cable", 60, 120, 350),
    ("Phone Tripod", 10, 500, 1100), ("Power Bank 20k", 12, 3500, 5500),
    ("Mini Speaker", 18, 900, 1800), ("Gaming Headset", 8, 2200, 3500),
    ("Smart Watch Ultra", 15, 2800, 4200), ("Car Mount", 35, 250, 650),
    ("OTG Adapter", 80, 80, 250)
]
for name, q, cost, prc in sample_items:
    c.execute("INSERT OR IGNORE INTO inventory VALUES(?,?,?,?)", (name, q, cost, prc))
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

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "👥 Customers & Ledger", "💰 Receiving", "🔄 Sales Return", "🤝 Capital Account"])

# 1. SALE INVOICE
with tabs[0]:
    st.subheader("New Sale")
    c_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    cust_sel = st.selectbox("Select Customer", c_list)
    final_cust = st.text_input("Walk-in Name", value="Walk-in Customer") if cust_sel == "Walk-in" else cust_sel
    
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    col1, col2 = st.columns(2)
    with col1: sel_item = st.selectbox("Item", inv_df['item']) if not inv_df.empty else None
    with col2: sel_qty = st.number_input("Qty", min_value=1, value=1)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    if st.button("➕ Add to Cart"):
        item_row = inv_df.loc[inv_df.item == sel_item]
        cost, price = item_row['cost'].values[0], item_row['price'].values[0]
        st.session_state.cart.append({"Item": sel_item, "Qty": sel_qty, "Cost": cost, "Price": price, "Total": sel_qty*price, "Profit": (price-cost)*sel_qty})
        st.rerun()

    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.table(cart_df)
        total_bill = cart_df['Total'].sum()
        total_profit = cart_df['Profit'].sum()
        st.write(f"### Total Bill: Rs {total_bill} | Expected Profit: Rs {total_profit}")
        
        if st.button("💾 Save & Print"):
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?,?)", (inv_no, datetime.now().strftime("%Y-%m-%d"), final_cust, total_bill, total_profit))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            st.session_state.cart = []
            st.success("Bill Saved!")
            st.rerun()

# 2. INVENTORY
with tabs[1]:
    st.subheader("Inventory Stock")
    with st.expander("Add/Update Stock"):
        ni, nq, nc, np = st.text_input("Item Name"), st.number_input("Qty", 0), st.number_input("Cost", 0), st.number_input("Sale Price", 0)
        if st.button("Save Item"):
            c.execute("INSERT OR REPLACE INTO inventory VALUES(?,?,?,?)", (ni, nq, nc, np))
            conn.commit()
            st.rerun()
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# 3. CUSTOMERS & LEDGER
with tabs[2]:
    st.subheader("Customer Ledger")
    with st.expander("Register Customer"):
        cn, cb = st.text_input("Name"), st.number_input("Opening Bal", 0)
        if st.button("Add Customer"):
            c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (cn, cb))
            conn.commit()
            st.rerun()
    
    all_c = pd.read_sql("SELECT * FROM customers", conn)
    ledger = []
    for _, r in all_c.iterrows():
        name = r['name']
        sales = pd.read_sql(f"SELECT SUM(total) FROM invoices WHERE customer='{name}'", conn).iloc[0,0] or 0
        rets = pd.read_sql(f"SELECT SUM(amount) FROM returns WHERE customer='{name}'", conn).iloc[0,0] or 0
        paid = pd.read_sql(f"SELECT SUM(amount) FROM payments WHERE customer='{name}'", conn).iloc[0,0] or 0
        ledger.append({"Customer": name, "Old Bal": r['opening_balance'], "Sales": sales, "Returns": rets, "Paid": paid, "Balance": r['opening_balance']+sales-rets-paid})
    st.table(pd.DataFrame(ledger))

# 4. RECEIVING
with tabs[3]:
    st.subheader("Receive Payment")
    names = [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    r_c = st.selectbox("Customer", names)
    r_a = st.number_input("Amount", 0)
    r_m = st.selectbox("Bank/Method", ["Cash", "Meezan Bank", "Faysal Bank", "EasyPaisa"])
    if st.button("Save Payment"):
        c.execute("INSERT INTO payments VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_c, r_a, r_m))
        conn.commit()
        st.success("Payment Recorded!")

# 5. SALES RETURN
with tabs[4]:
    st.subheader("Return Item")
    ret_c = st.selectbox("From Customer ", ["Walk-in"] + names)
    ret_i = st.selectbox("Item Name ", inv_df['item'])
    ret_q = st.number_input("Return Qty", 1)
    ret_v = st.number_input("Return Amount (Value)", 0)
    if st.button("Confirm Return"):
        c.execute("INSERT INTO returns VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), ret_c, ret_i, ret_q, ret_v))
        c.execute("UPDATE inventory SET qty = qty + ? WHERE item = ?", (ret_q, ret_i))
        conn.commit()
        st.success("Stock updated and customer balance adjusted!")

# 6. CAPITAL ACCOUNT
with tabs[5]:
    st.subheader("Partners Investment (Capital)")
    p_name = st.selectbox("Select Partner", ["M Waqas", "Farid Khan", "Farman Ali"])
    p_amt = st.number_input("Investment Amount", 0)
    p_type = st.selectbox("Transaction Type", ["Investment (In)", "Withdrawal (Out)"])
    if st.button("Save Capital Entry"):
        c.execute("INSERT INTO capital VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), p_name, p_amt, p_type))
        conn.commit()
        st.success("Capital Account Updated!")
    
    st.write("### Partner Summaries")
    for p in ["M Waqas", "Farid Khan", "Farman Ali"]:
        invest = pd.read_sql(f"SELECT SUM(amount) FROM capital WHERE partner='{p}' AND type LIKE 'Investment%'", conn).iloc[0,0] or 0
        draw = pd.read_sql(f"SELECT SUM(amount) FROM capital WHERE partner='{p}' AND type LIKE 'Withdrawal%'", conn).iloc[0,0] or 0
        st.write(f"**{p}**: Total Investment: {invest} | Total Withdrawal: {draw} | Current Capital: {invest-draw}")
