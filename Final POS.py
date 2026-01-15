import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# --- Database & Auto-Update Logic ---
def init_db():
    conn = sqlite3.connect('waa_mobile_pos.db')
    c = conn.cursor()
    
    # Tables creation
    c.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, cost_price REAL, stock INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, customer_name TEXT, total REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY, name TEXT, balance_payable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT, balance_receivable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS capital (partner TEXT PRIMARY KEY, investment REAL, withdrawals REAL, profit_share REAL)')
    
    # --- Fix for DatabaseError (Adding missing columns if they don't exist) ---
    try:
        c.execute("SELECT withdrawals FROM capital LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE capital ADD COLUMN withdrawals REAL DEFAULT 0.0")
    
    # Testing Data for WAA AA Mobile Accessories
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        items = [('Samsung Charger', 450, 50), ('IPhone Cable', 300, 40), ('Handsfree MI', 150, 100),
                 ('Power Bank', 2500, 10), ('Glass Protector', 50, 200), ('Back Cover', 120, 80),
                 ('Airpods Pro', 1800, 15), ('Memory Card 32GB', 600, 30), ('Battery Nokia', 250, 25)]
        c.executemany("INSERT INTO inventory (item_name, cost_price, stock) VALUES (?,?,?)", items)
        
        c.executemany("INSERT INTO suppliers (name, balance_payable) VALUES (?,?)", 
                      [('ABC Accessories', 50000), ('Hall Road Wholesaler', 25000)])
        
        c.executemany("INSERT INTO customers (name, balance_receivable) VALUES (?,?)", 
                      [('Aslam Mobile', 1200), ('Khan Communication', 5000), ('City Shop', 3400)])
        
        for p in ['M Waqas', 'Farid Khan', 'Farman Ali']:
            c.execute("INSERT OR IGNORE INTO capital (partner, investment, withdrawals, profit_share) VALUES (?,?,?,?)", (p, 0.0, 0.0, 0.0))
            
    conn.commit()
    conn.close()

init_db()

# --- Login System ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.sidebar.title("🔐 Login")
    user = st.sidebar.text_input("Username")
    pw = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if user == "admin" and pw == "waa123":
            st.session_state['logged_in'] = True
            st.rerun()
        else: st.sidebar.error("Ghalat details!")
    st.stop()

# --- UI Header (As per your Card) ---
st.title("📱 WAA AA Mobile Accessories")
st.markdown("""
**Shop T-27, 3rd Floor, Hassan Center 2, Hall Road, Lahore.** **Contact:** M. Waqas (0304-4724435, 0315-4899075) | Farman Ali (0303-0075400) | Fareed Ahmed (0328-4080860)
---
""")

tabs = st.tabs(["Invoice/Billing", "Receiving", "Inventory", "Suppliers", "Customers", "Expenses", "Capital A/C", "Reports"])

# 1. Invoice
with tabs[0]:
    st.header("New Order")
    conn = sqlite3.connect('waa_mobile_pos.db')
    cust_list = pd.read_sql("SELECT name FROM customers", conn)['name'].tolist()
    prod_df = pd.read_sql("SELECT item_name FROM inventory", conn)
    
    customer = st.selectbox("Select Customer", cust_list)
    product = st.selectbox("Select Product", prod_df['item_name'])
    qty = st.number_input("Quantity", min_value=1, value=1)
    s_price = st.number_input("Sale Price", min_value=0.0)
    
    total_bill = qty * s_price
    st.subheader(f"Total Bill: Rs. {total_bill}")
    
    if st.button("Generate & Save Bill"):
        c = conn.cursor()
        c.execute("INSERT INTO sales (customer_name, total, date) VALUES (?,?,?)", (customer, total_bill, datetime.now().strftime('%Y-%m-%d')))
        c.execute("UPDATE customers SET balance_receivable = balance_receivable + ? WHERE name = ?", (total_bill, customer))
        c.execute("UPDATE inventory SET stock = stock - ? WHERE item_name = ?", (qty, product))
        conn.commit()
        st.success("Bill saved successfully!")
    conn.close()

# 2. Receiving
with tabs[1]:
    st.header("Receive Payment")
    conn = sqlite3.connect('waa_mobile_pos.db')
    c_pay = st.selectbox("Customer Name", pd.read_sql("SELECT name FROM customers", conn))
    amt_rec = st.number_input("Amount Received", min_value=0.0)
    if st.button("Confirm Payment"):
        conn.execute("UPDATE customers SET balance_receivable = balance_receivable - ? WHERE name = ?", (amt_rec, c_pay))
        conn.commit()
        st.success("Payment recorded!")
    conn.close()

# 5. Expenses
with tabs[5]:
    st.header("Add Shop Expense")
    e_desc = st.text_input("Detail (e.g. Bijli Bill, Tea)")
    e_amt = st.number_input("Amount", min_value=0.0, key="exp_amt")
    if st.button("Save Expense"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("INSERT INTO expenses (description, amount, date) VALUES (?,?,?)", (e_desc, e_amt, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        st.success("Expense added!")
    
    st.subheader("Expense History")
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM expenses", conn), use_container_width=True)
    conn.close()

# 6. Capital Account
with tabs[6]:
    st.header("Partners Capital")
    partner = st.selectbox("Partner", ["M Waqas", "Farid Khan", "Farman Ali"])
    type_cap = st.radio("Action", ["Investment", "Withdrawal"])
    cap_val = st.number_input("Amount", min_value=0.0, key="cap_val")
    
    if st.button("Update Capital"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        if type_cap == "Investment":
            conn.execute("UPDATE capital SET investment = investment + ? WHERE partner = ?", (cap_val, partner))
        else:
            conn.execute("UPDATE capital SET withdrawals = withdrawals + ? WHERE partner = ?", (cap_val, partner))
        conn.commit()
        st.success("Capital Updated!")
    
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT partner, investment, withdrawals FROM capital", conn))
    conn.close()

# 7. Reports
with tabs[7]:
    st.header("Business Reports")
    conn = sqlite3.connect('waa_mobile_pos.db')
    sales = pd.read_sql("SELECT * FROM sales", conn)
    exps = pd.read_sql("SELECT * FROM expenses", conn)
    
    col1, col2 = st.columns(2)
    col1.metric("Total Sales", f"Rs. {sales['total'].sum()}")
    col2.metric("Total Expenses", f"Rs. {exps['amount'].sum()}")
    
    st.subheader("Sales History")
    st.dataframe(sales, use_container_width=True)
    conn.close()

# Other tabs (Inventory, Suppliers, Customers) are same
with tabs[2]:
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
    conn.close()
with tabs[3]:
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT name, balance_payable FROM suppliers", conn))
    conn.close()
with tabs[4]:
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT name, balance_receivable FROM customers", conn))
    conn.close()
