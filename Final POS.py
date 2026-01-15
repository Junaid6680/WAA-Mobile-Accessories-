import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
import io

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect('waa_mobile_pos.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, cost_price REAL, stock INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, customer_name TEXT, total REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY, name TEXT, balance_payable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT, balance_receivable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS capital (partner TEXT PRIMARY KEY, investment REAL, withdrawals REAL, profit_share REAL)')
    
    # Testing Data Insertion (Requirement #2: Suppliers)
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        items = [('Samsung Charger', 450, 50), ('IPhone Cable', 300, 40), ('Handsfree MI', 150, 100),
                 ('Power Bank', 2500, 10), ('Glass Protector', 50, 200), ('Back Cover', 120, 80),
                 ('Airpods Pro', 1800, 15), ('Memory Card 32GB', 600, 30), ('Battery Nokia', 250, 25),
                 ('Type-C Adapter', 80, 60), ('Car Charger', 350, 20), ('Bluetooth Speaker', 1200, 12),
                 ('Ring Light', 950, 8), ('USB 64GB', 850, 25), ('Selfie Stick', 200, 15)]
        c.executemany("INSERT INTO inventory (item_name, cost_price, stock) VALUES (?,?,?)", items)
        
        # Suppliers Added for Testing
        c.executemany("INSERT INTO suppliers (name, balance_payable) VALUES (?,?)", 
                      [('ABC Accessories', 50000), ('Hall Road Wholesaler', 25000)])
        
        c.executemany("INSERT INTO customers (name, balance_receivable) VALUES (?,?)", 
                      [('Aslam Mobile', 1200), ('Khan Communication', 5000), ('City Shop', 3400)])
        
        for p in ['M Waqas', 'Farid Khan', 'Farman Ali']:
            c.execute("INSERT OR IGNORE INTO capital (partner, investment, withdrawals, profit_share) VALUES (?,?,?,?)", (p, 0.0, 0.0, 0.0))
            
    conn.commit()
    conn.close()

init_db()

# --- Login Logic ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.sidebar.title("🔐 Shop Login")
    user = st.sidebar.text_input("Username")
    pw = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if user == "admin" and pw == "waa123":
            st.session_state['logged_in'] = True
            st.rerun()
        else: st.sidebar.error("Ghalat Password!")
    st.warning("Pehle Login Karein")
    st.stop()

# --- Main UI ---
st.title("📱 WAA AA Mobile Accessories")
tabs = st.tabs(["Invoice/Billing", "Receiving", "Inventory", "Suppliers", "Customers", "Expenses", "Capital A/C", "Reports"])

# 1. Invoice (Requirement #1: Total bill at the end)
with tabs[0]:
    st.header("New Order / Bill")
    conn = sqlite3.connect('waa_mobile_pos.db')
    cust_list = pd.read_sql("SELECT name FROM customers", conn)['name'].tolist()
    prod_df = pd.read_sql("SELECT item_name, stock FROM inventory", conn)
    
    col1, col2 = st.columns(2)
    with col1: customer = st.selectbox("Select Customer", cust_list)
    with col2: product = st.selectbox("Select Product", prod_df['item_name'])
    
    qty = st.number_input("Quantity", min_value=1, value=1)
    s_price = st.number_input("Sale Price", min_value=0.0)
    
    total_bill = qty * s_price
    st.markdown(f"### **Total Amount: Rs. {total_bill}**") # Bill shown at last
    
    if st.button("Generate Bill & Save"):
        c = conn.cursor()
        c.execute("INSERT INTO sales (customer_name, total, date) VALUES (?,?,?)", (customer, total_bill, datetime.now().strftime('%Y-%m-%d')))
        c.execute("UPDATE customers SET balance_receivable = balance_receivable + ? WHERE name = ?", (total_bill, customer))
        c.execute("UPDATE inventory SET stock = stock - ? WHERE item_name = ?", (qty, product))
        conn.commit()
        st.success("Bill Saved successfully!")
    conn.close()

# 2. Receiving
with tabs[1]:
    st.header("Receive Payment")
    conn = sqlite3.connect('waa_mobile_pos.db')
    c_name = st.selectbox("From Customer", pd.read_sql("SELECT name FROM customers", conn))
    amt = st.number_input("Amount Received", min_value=0.0)
    if st.button("Update Payment"):
        conn.execute("UPDATE customers SET balance_receivable = balance_receivable - ? WHERE name = ?", (amt, c_name))
        conn.commit()
        st.success("Payment Received!")
    conn.close()

# 3. Inventory
with tabs[2]:
    st.header("Current Stock")
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
    conn.close()

# 4. Suppliers (Requirement #2: Test data added in init_db)
with tabs[3]:
    st.header("Supplier Balances")
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT name, balance_payable FROM suppliers", conn))
    conn.close()

# 5. Customers
with tabs[4]:
    st.header("Customer Balances")
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT name, balance_receivable FROM customers", conn))
    conn.close()

# 6. Expenses (Requirement #3: Detail adding option)
with tabs[5]:
    st.header("Shop Expenses")
    desc = st.text_input("Expense Description (e.g., Tea, Electricity Bill)")
    e_amt = st.number_input("Expense Amount", min_value=0.0)
    if st.button("Save Expense"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("INSERT INTO expenses (description, amount, date) VALUES (?,?,?)", (desc, e_amt, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        st.success("Expense Recorded!")
    
    st.subheader("Expense History")
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM expenses", conn), use_container_width=True)
    conn.close()

# 7. Capital Account (Requirement #4: Investment & Withdrawal)
with tabs[6]:
    st.header("Partners Capital Account")
    partner = st.selectbox("Select Partner", ["M Waqas", "Farid Khan", "Farman Ali"])
    opt = st.radio("Transaction Type", ["Investment (Add Money)", "Withdrawal (Take Money)"])
    cap_amt = st.number_input("Amount", min_value=0.0)
    
    if st.button("Update Capital Account"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        if opt == "Investment (Add Money)":
            conn.execute("UPDATE capital SET investment = investment + ? WHERE partner = ?", (cap_amt, partner))
        else:
            conn.execute("UPDATE capital SET withdrawals = withdrawals + ? WHERE partner = ?", (cap_amt, partner))
        conn.commit()
        st.success("Account Updated!")
    
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT partner, investment, withdrawals FROM capital", conn))
    conn.close()

# 8. Reports (Requirement #5: Daily, Weekly, Monthly)
with tabs[7]:
    st.header("Sales & Business Reports")
    rep_opt = st.selectbox("Report Filter", ["Daily", "Weekly", "Monthly", "Yearly"])
    
    conn = sqlite3.connect('waa_mobile_pos.db')
    sales_df = pd.read_sql("SELECT * FROM sales", conn)
    exp_df = pd.read_sql("SELECT * FROM expenses", conn)
    
    # Simple Date Filter Logic
    today = datetime.now().date()
    if rep_opt == "Daily": sales_df = sales_df[sales_df['date'] == str(today)]
    
    st.subheader(f"{rep_opt} Sales Summary")
    st.dataframe(sales_df)
    st.write(f"Total Sales: Rs. {sales_df['total'].sum()}")
    
    st.subheader(f"{rep_opt} Expense Summary")
    st.write(f"Total Expenses: Rs. {exp_df['amount'].sum()}")
    conn.close()
