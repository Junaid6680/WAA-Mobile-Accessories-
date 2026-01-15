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
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY, 
        customer_name TEXT, 
        walkin_info TEXT, 
        total REAL, 
        date TEXT, 
        invoice_no TEXT, 
        payment_method TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY, name TEXT, balance_payable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT, balance_receivable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, type TEXT, voucher_no TEXT, party_name TEXT, amount REAL, method TEXT, date TEXT)')
    
    # Partners and Testing Data
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO inventory (item_name, cost_price, stock) VALUES (?,?,?)", 
                      [('Samsung Charger', 450, 50), ('IPhone Cable', 300, 40)])
        c.executemany("INSERT INTO customers (name, balance_receivable) VALUES (?,?)", 
                      [('Aslam Mobile', 0), ('Khan Communication', 0)])
        c.executemany("INSERT INTO suppliers (name, balance_payable) VALUES (?,?)", 
                      [('ABC Accessories', 5000), ('Hall Road Wholesaler', 10000)])
    conn.commit()
    conn.close()

init_db()

# --- Utility Functions ---
def get_next_id(prefix):
    return f"{prefix}-{datetime.now().strftime('%y%m%d%H%M%S')}"

# --- Main Logic ---
st.title("📱 WAA AA Mobile Accessories")
st.info("Contacts: M. Waqas (0315-4899075) | Farman Ali (0303-0075400) | Fareed Ahmed (0328-4080860)")

tabs = st.tabs(["Invoice", "Inventory", "Suppliers (Pay)", "Customers (Rec)", "Capital", "Expenses", "Reports"])

# 1. Invoice (Sales)
with tabs[0]:
    if 'bill_items' not in st.session_state: st.session_state['bill_items'] = []
    conn = sqlite3.connect('waa_mobile_pos.db')
    custs = ["Walk-in Customer"] + pd.read_sql("SELECT name FROM customers", conn)['name'].tolist()
    prods = pd.read_sql("SELECT item_name FROM inventory", conn)
    
    customer = st.selectbox("Select Customer", custs)
    walkin_detail = st.text_input("Walk-in Name/Phone") if customer == "Walk-in Customer" else ""
    pay_method = st.selectbox("Payment Method", ["Cash", "JazzCash", "EasyPaisa", "Faysal Bank", "Meezan Bank"])
    
    col1, col2, col3 = st.columns([2,1,1])
    with col1: prod = st.selectbox("Product", prods['item_name'])
    with col2: q = st.number_input("Qty", 1)
    with col3: pr = st.number_input("Price", 0.0)
    
    if st.button("Add Item"):
        st.session_state['bill_items'].append({'item': prod, 'qty': q, 'price': pr, 'total': q*pr})
    
    if st.session_state['bill_items']:
        df_bill = pd.DataFrame(st.session_state['bill_items'])
        st.table(df_bill)
        gt = df_bill['total'].sum()
        
        if st.button("Finalize & Generate Invoice"):
            inv_no = get_next_id("INV")
            date_now = datetime.now().strftime('%Y-%m-%d %H:%M')
            c = conn.cursor()
            c.execute("INSERT INTO sales (customer_name, walkin_info, total, date, invoice_no, payment_method) VALUES (?,?,?,?,?,?)", 
                      (customer, walkin_detail, gt, date_now, inv_no, pay_method))
            if customer != "Walk-in Customer":
                c.execute("UPDATE customers SET balance_receivable = balance_receivable + ? WHERE name = ?", (gt, customer))
            for i in st.session_state['bill_items']:
                c.execute("UPDATE inventory SET stock = stock - ? WHERE item_name = ?", (i['qty'], i['item']))
            conn.commit()
            st.success(f"Invoice {inv_no} Saved on {date_now}!")
            st.session_state['bill_items'] = []
            st.rerun()
    conn.close()

# 2. Suppliers (Pay Voucher)
with tabs[2]:
    st.header("Supplier Payment Voucher")
    conn = sqlite3.connect('waa_mobile_pos.db')
    sups = pd.read_sql("SELECT name FROM suppliers", conn)['name'].tolist()
    sel_sup = st.selectbox("Select Supplier", sups)
    p_amt = st.number_input("Pay Amount", 0.0)
    p_method = st.selectbox("Pay From", ["Cash", "JazzCash", "EasyPaisa", "Faysal Bank", "Meezan Bank"], key="p_sup")
    
    if st.button("Confirm Payment (Pay Voucher)"):
        p_vouc = get_next_id("PAY")
        date_now = datetime.now().strftime('%Y-%m-%d %H:%M')
        conn.execute("INSERT INTO transactions (type, voucher_no, party_name, amount, method, date) VALUES (?,?,?,?,?,?)",
                     ('Supplier Pay', p_vouc, sel_sup, p_amt, p_method, date_now))
        conn.execute("UPDATE suppliers SET balance_payable = balance_payable - ? WHERE name = ?", (p_amt, sel_sup))
        conn.commit()
        st.success(f"Voucher {p_vouc} Generated! Balance Updated.")
    st.subheader("Suppliers Balance List")
    st.dataframe(pd.read_sql("SELECT * FROM suppliers", conn))
    conn.close()

# 3. Customers (Receiving Voucher)
with tabs[3]:
    st.header("Customer Receiving Voucher")
    conn = sqlite3.connect('waa_mobile_pos.db')
    c_list = pd.read_sql("SELECT name FROM customers", conn)['name'].tolist()
    sel_c = st.selectbox("Customer Name", c_list)
    r_amt = st.number_input("Received Amount", 0.0)
    r_method = st.selectbox("Received In", ["Cash", "JazzCash", "EasyPaisa", "Faysal Bank", "Meezan Bank"], key="r_cust")
    
    if st.button("Confirm Receiving (Rec Voucher)"):
        r_vouc = get_next_id("REC")
        date_now = datetime.now().strftime('%Y-%m-%d %H:%M')
        conn.execute("INSERT INTO transactions (type, voucher_no, party_name, amount, method, date) VALUES (?,?,?,?,?,?)",
                     ('Customer Rec', r_vouc, sel_c, r_amt, r_method, date_now))
        conn.execute("UPDATE customers SET balance_receivable = balance_receivable - ? WHERE name = ?", (r_amt, sel_c))
        conn.commit()
        st.success(f"Voucher {r_vouc} Generated on {date_now}!")
    st.subheader("Customers Balance List")
    st.dataframe(pd.read_sql("SELECT * FROM customers", conn))
    conn.close()

# 4. Expenses (Review & Fixed)
with tabs[5]:
    st.header("Shop Expenses")
    e_desc = st.text_input("Expense Description")
    e_amt = st.number_input("Amount", 0.0, key="exp_amt")
    if st.button("Save Expense"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("INSERT INTO expenses (description, amount, date) VALUES (?,?,?)", (e_desc, e_amt, datetime.now().strftime('%Y-%m-%d %H:%M')))
        conn.commit()
        st.success("Expense Saved!")
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM expenses", conn))
    conn.close()

# 5. Reports (Financial Summary)
with tabs[6]:
    st.header("Cash & Bank Summary")
    conn = sqlite3.connect('waa_mobile_pos.db')
    
    # Summary of Sales + Receiving - Payments
    methods = ["Cash", "JazzCash", "EasyPaisa", "Faysal Bank", "Meezan Bank"]
    summary_data = []
    
    for m in methods:
        sales_m = pd.read_sql(f"SELECT SUM(total) FROM sales WHERE payment_method='{m}'", conn).iloc[0,0] or 0
        rec_m = pd.read_sql(f"SELECT SUM(amount) FROM transactions WHERE method='{m}' AND type='Customer Rec'", conn).iloc[0,0] or 0
        pay_m = pd.read_sql(f"SELECT SUM(amount) FROM transactions WHERE method='{m}' AND type='Supplier Pay'", conn).iloc[0,0] or 0
        net = (sales_m + rec_m) - pay_m
        summary_data.append({"Method": m, "Net Balance": net})
    
    st.table(pd.DataFrame(summary_data))
    
    st.subheader("Transaction History (Vouchers)")
    st.dataframe(pd.read_sql("SELECT * FROM transactions ORDER BY id DESC", conn))
    
    st.subheader("Sales History (Invoices)")
    st.dataframe(pd.read_sql("SELECT * FROM sales ORDER BY id DESC", conn))
    conn.close()
