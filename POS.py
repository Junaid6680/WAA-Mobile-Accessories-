import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- Database & Auto-Update Logic ---
def init_db():
    conn = sqlite3.connect('waa_mobile_pos.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, cost_price REAL, stock INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, customer_name TEXT, total REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY, name TEXT, balance_payable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT, balance_receivable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS capital (partner TEXT PRIMARY KEY, opening_balance REAL, investment REAL, withdrawals REAL, profit_share REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS returns (id INTEGER PRIMARY KEY, item_name TEXT, qty INTEGER, amount REAL, date TEXT)')
    
    # Auto-Fix for missing columns
    try:
        c.execute("SELECT opening_balance FROM capital LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE capital ADD COLUMN opening_balance REAL DEFAULT 0.0")

    # Testing Data
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        items = [('Samsung Charger', 450, 50), ('IPhone Cable', 300, 40), ('Handsfree MI', 150, 100), ('Power Bank', 2500, 10)]
        c.executemany("INSERT INTO inventory (item_name, cost_price, stock) VALUES (?,?,?)", items)
        for p in ['M Waqas', 'Farid Khan', 'Farman Ali']:
            c.execute("INSERT OR IGNORE INTO capital (partner, opening_balance, investment, withdrawals, profit_share) VALUES (?,?,?,?,?)", (p, 0.0, 0.0, 0.0, 0.0))
        c.executemany("INSERT OR IGNORE INTO customers (name, balance_receivable) VALUES (?,?)", [('Aslam Mobile', 0.0), ('Khan Communication', 0.0)])

    conn.commit()
    conn.close()

init_db()

# --- Login Logic ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if not st.session_state['logged_in']:
    user = st.sidebar.text_input("Username")
    pw = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if user == "admin" and pw == "waa123":
            st.session_state['logged_in'] = True
            st.rerun()
    st.stop()

# --- Header ---
st.title("📱 WAA AA Mobile Accessories")
st.markdown("**Shop T-27, 3rd Floor, Hassan Center 2, Hall Road, Lahore.**")

tabs = st.tabs(["Invoice/Billing", "Returns", "Receiving", "Inventory", "Capital A/C", "Expenses", "Reports"])

# 1. Multi-Item Invoice (Requirement #1)
with tabs[0]:
    st.header("New Order (Multi-Item)")
    if 'bill_items' not in st.session_state: st.session_state['bill_items'] = []
    
    conn = sqlite3.connect('waa_mobile_pos.db')
    cust_list = pd.read_sql("SELECT name FROM customers", conn)['name'].tolist()
    prod_df = pd.read_sql("SELECT item_name FROM inventory", conn)
    
    customer = st.selectbox("Select Customer", cust_list)
    
    col1, col2, col3 = st.columns([3,1,1])
    with col1: prod = st.selectbox("Product", prod_df['item_name'])
    with col2: q = st.number_input("Qty", min_value=1, value=1)
    with col3: p = st.number_input("Price", min_value=0.0)
    
    if st.button("Add Item to List"):
        st.session_state['bill_items'].append({'item': prod, 'qty': q, 'price': p, 'total': q*p})
    
    if st.session_state['bill_items']:
        bill_df = pd.DataFrame(st.session_state['bill_items'])
        st.table(bill_df)
        grand_total = bill_df['total'].sum()
        st.subheader(f"Grand Total: Rs. {grand_total}")
        
        if st.button("Finalize & Save Bill"):
            c = conn.cursor()
            c.execute("INSERT INTO sales (customer_name, total, date) VALUES (?,?,?)", (customer, grand_total, datetime.now().strftime('%Y-%m-%d')))
            c.execute("UPDATE customers SET balance_receivable = balance_receivable + ? WHERE name = ?", (grand_total, customer))
            for item in st.session_state['bill_items']:
                c.execute("UPDATE inventory SET stock = stock - ? WHERE item_name = ?", (item['qty'], item['item']))
            conn.commit()
            st.session_state['bill_items'] = []
            st.success("Complete Bill Saved!")
    conn.close()

# 2. Returns Tab (Requirement #3)
with tabs[1]:
    st.header("Item Returns")
    conn = sqlite3.connect('waa_mobile_pos.db')
    ret_prod = st.selectbox("Return Item", pd.read_sql("SELECT item_name FROM inventory", conn)['item_name'].tolist())
    ret_qty = st.number_input("Return Qty", min_value=1)
    ret_amt = st.number_input("Refund Amount", min_value=0.0)
    if st.button("Process Return"):
        c = conn.cursor()
        c.execute("INSERT INTO returns (item_name, qty, amount, date) VALUES (?,?,?,?)", (ret_prod, ret_qty, ret_amt, datetime.now().strftime('%Y-%m-%d')))
        c.execute("UPDATE inventory SET stock = stock + ? WHERE item_name = ?", (ret_qty, ret_prod))
        conn.commit()
        st.success("Stock Updated and Return Recorded!")
    conn.close()

# 3. Capital Account (Requirement #2: Opening Balance)
with tabs[4]:
    st.header("Capital & Opening Balance")
    partner = st.selectbox("Partner", ["M Waqas", "Farid Khan", "Farman Ali"])
    op_bal = st.number_input("Set Opening Balance", min_value=0.0)
    if st.button("Update Opening Balance"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("UPDATE capital SET opening_balance = ? WHERE partner = ?", (op_bal, partner))
        conn.commit()
        st.success("Opening Balance Set!")
    
    # Investment/Withdrawal
    type_cap = st.radio("Action", ["Investment", "Withdrawal"])
    cap_val = st.number_input("Amount", min_value=0.0)
    if st.button("Submit Transaction"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        col = "investment" if type_cap == "Investment" else "withdrawals"
        conn.execute(f"UPDATE capital SET {col} = {col} + ? WHERE partner = ?", (cap_val, partner))
        conn.commit()
        st.success("Account Updated!")
    
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT partner, opening_balance, investment, withdrawals FROM capital", conn))
    conn.close()

# --- Other tabs logic (Inventory, Receiving, Reports) ---
with tabs[2]: # Receiving
    st.header("Receive Payment")
    conn = sqlite3.connect('waa_mobile_pos.db')
    c_pay = st.selectbox("Customer", pd.read_sql("SELECT name FROM customers", conn)['name'].tolist())
    amt_rec = st.number_input("Rec. Amount", min_value=0.0)
    if st.button("Confirm"):
        conn.execute("UPDATE customers SET balance_receivable = balance_receivable - ? WHERE name = ?", (amt_rec, c_pay))
        conn.commit()
        st.success("Received!")
    conn.close()
with tabs[3]: # Inventory
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
    conn.close()
with tabs[6]: # Reports
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.metric("Total Sales", f"Rs. {pd.read_sql('SELECT SUM(total) FROM sales', conn).iloc[0,0] or 0}")
    st.subheader("Returns History")
    st.dataframe(pd.read_sql("SELECT * FROM returns", conn), use_container_width=True)
    conn.close()
