import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
import io

# --- Database Initialization with Testing Data ---
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

    # Testing Data Insertion
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        # 15 Items
        items = [('Samsung Charger', 450, 50), ('IPhone Cable', 300, 40), ('Handsfree MI', 150, 100),
                 ('Power Bank', 2500, 10), ('Glass Protector', 50, 200), ('Back Cover', 120, 80),
                 ('Airpods Pro', 1800, 15), ('Memory Card 32GB', 600, 30), ('Battery Nokia', 250, 25),
                 ('Type-C Adapter', 80, 60), ('Car Charger', 350, 20), ('Bluetooth Speaker', 1200, 12),
                 ('Ring Light', 950, 8), ('USB 64GB', 850, 25), ('Selfie Stick', 200, 15)]
        c.executemany("INSERT INTO inventory (item_name, cost_price, stock) VALUES (?,?,?)", items)
        
        # 2 Suppliers
        c.executemany("INSERT INTO suppliers (name, balance_payable) VALUES (?,?)", 
                      [('ABC Accessories', 50000), ('Hall Road Wholesaler', 25000)])
        
        # 3 Customers
        c.executemany("INSERT INTO customers (name, balance_receivable) VALUES (?,?)", 
                      [('Aslam Mobile', 1200), ('Khan Communication', 5000), ('City Shop', 3400)])
        
        # Partners
        for p in ['M Waqas', 'Farman Ali', 'Fareed Ahmed']:
            c.execute("INSERT OR IGNORE INTO capital (partner, opening_balance, investment, withdrawals, profit_share) VALUES (?,?,?,?,?)", (p, 0.0, 0.0, 0.0, 0.0))

    conn.commit()
    conn.close()

init_db()

# --- Thermal PDF Function (80mm) ---
def create_thermal_pdf(customer, items, grand_total):
    receipt_width = 226 
    receipt_height = 350 + (len(items) * 20)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=(receipt_width, receipt_height))
    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(113, receipt_height - 20, "WAA AA MOBILE ACCESSORIES")
    p.setFont("Helvetica", 7)
    p.drawCentredString(113, receipt_height - 35, "Shop T-27, Hall Road, Lahore")
    p.line(10, receipt_height - 45, 216, receipt_height - 45)
    p.drawString(10, receipt_height - 60, f"Cust: {customer}")
    p.drawString(10, receipt_height - 72, f"Date: {datetime.now().strftime('%d-%m-%y %H:%M')}")
    p.line(10, receipt_height - 80, 216, receipt_height - 80)
    y = receipt_height - 95
    for item in items:
        p.drawString(10, y, f"{item['item'][:15]} x{item['qty']}  {int(item['total'])}")
        y -= 15
    p.line(10, y, 216, y)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(10, y - 20, f"TOTAL: Rs. {int(grand_total)}")
    p.save()
    buffer.seek(0)
    return buffer

# --- Main Logic ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if not st.session_state['logged_in']:
    u, p = st.sidebar.text_input("User"), st.sidebar.text_input("Pass", type="password")
    if st.sidebar.button("Login"):
        if u == "admin" and p == "waa123":
            st.session_state['logged_in'] = True
            st.rerun()
    st.stop()

# Address & Contacts (Requirement)
st.title("📱 WAA AA Mobile Accessories")
st.info("Shop T-27, 3rd Floor, Hassan Center 2, Hall Road, Lahore.\n\nContacts: M. Waqas (0304-4724435) | Farman Ali (0303-0075400) | Fareed Ahmed (0328-4080860)")

tabs = st.tabs(["Invoice", "Inventory", "Suppliers", "Customers", "Receiving", "Returns", "Capital", "Expenses", "Reports"])

# 1. Invoice (Multi-Item)
with tabs[0]:
    if 'bill_items' not in st.session_state: st.session_state['bill_items'] = []
    conn = sqlite3.connect('waa_mobile_pos.db')
    custs = pd.read_sql("SELECT name FROM customers", conn)['name'].tolist()
    prods = pd.read_sql("SELECT item_name FROM inventory", conn)
    
    customer = st.selectbox("Select Customer", custs)
    col1, col2, col3 = st.columns([2,1,1])
    with col1: prod = st.selectbox("Product", prods['item_name'])
    with col2: q = st.number_input("Qty", 1, key="q_inv")
    with col3: pr = st.number_input("Price", 0.0, key="p_inv")
    
    if st.button("Add Item to Bill"):
        st.session_state['bill_items'].append({'item': prod, 'qty': q, 'price': pr, 'total': q*pr})
    
    if st.session_state['bill_items']:
        df_bill = pd.DataFrame(st.session_state['bill_items'])
        st.table(df_bill)
        gt = df_bill['total'].sum()
        st.subheader(f"Grand Total: Rs. {gt}")
        
        if st.button("Finalize & Save Bill"):
            c = conn.cursor()
            c.execute("INSERT INTO sales (customer_name, total, date) VALUES (?,?,?)", (customer, gt, datetime.now().strftime('%Y-%m-%d')))
            c.execute("UPDATE customers SET balance_receivable = balance_receivable + ? WHERE name = ?", (gt, customer))
            for i in st.session_state['bill_items']:
                c.execute("UPDATE inventory SET stock = stock - ? WHERE item_name = ?", (i['qty'], i['item']))
            conn.commit()
            pdf = create_thermal_pdf(customer, st.session_state['bill_items'], gt)
            st.download_button("📥 Print Thermal Receipt", pdf, f"Bill_{customer}.pdf", "application/pdf")
            st.session_state['bill_items'] = []
            st.success("Bill Saved and Stock Updated!")
    conn.close()

# 2. Inventory (Requirement: 15 items)
with tabs[1]:
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
    conn.close()

# 3. Suppliers (Requirement: 2 Suppliers)
with tabs[2]:
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM suppliers", conn), use_container_width=True)
    conn.close()

# 4. Customers (Requirement: 3 Customers)
with tabs[3]:
    st.header("Manage Customers")
    c_name = st.text_input("New Customer Name")
    if st.button("Add Customer"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("INSERT INTO customers (name, balance_receivable) VALUES (?,0)", (c_name,))
        conn.commit()
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM customers", conn), use_container_width=True)
    conn.close()

# 5. Receiving
with tabs[4]:
    conn = sqlite3.connect('waa_mobile_pos.db')
    c_list = pd.read_sql("SELECT name FROM customers", conn)['name'].tolist()
    sel_c = st.selectbox("Customer", c_list, key="c_rec")
    amt = st.number_input("Amount Received", 0.0)
    if st.button("Confirm Cash"):
        conn.execute("UPDATE customers SET balance_receivable = balance_receivable - ? WHERE name = ?", (amt, sel_c))
        conn.commit()
        st.success("Payment Received!")
    conn.close()

# 6. Returns
with tabs[5]:
    st.header("Stock Return")
    conn = sqlite3.connect('waa_mobile_pos.db')
    ret_itm = st.selectbox("Item", pd.read_sql("SELECT item_name FROM inventory", conn)['item_name'].tolist())
    ret_q = st.number_input("Qty to Return", 1)
    if st.button("Submit Return"):
        conn.execute("UPDATE inventory SET stock = stock + ? WHERE item_name = ?", (ret_q, ret_itm))
        conn.commit()
        st.success("Stock returned successfully!")
    conn.close()

# 7. Capital
with tabs[6]:
    st.header("Partner Capital")
    p_name = st.selectbox("Partner", ["M Waqas", "Farman Ali", "Fareed Ahmed"])
    o_bal = st.number_input("Opening Balance", 0.0)
    if st.button("Save Opening Balance"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("UPDATE capital SET opening_balance = ? WHERE partner = ?", (o_bal, p_name))
        conn.commit()
    
    t_type = st.radio("Type", ["Investment", "Withdrawal"])
    t_amt = st.number_input("Amount", 0.0, key="t_cap")
    if st.button("Update Account"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        col = "investment" if t_type == "Investment" else "withdrawals"
        conn.execute(f"UPDATE capital SET {col} = {col} + ? WHERE partner = ?", (t_amt, p_name))
        conn.commit()
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT partner, opening_balance, investment, withdrawals FROM capital", conn))
    conn.close()

# 8. Expenses
with tabs[7]:
    e_d = st.text_input("Detail")
    e_a = st.number_input("Amount", 0.0, key="e_amt")
    if st.button("Add Expense"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("INSERT INTO expenses (description, amount, date) VALUES (?,?,?)", (e_d, e_a, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM expenses", conn))
    conn.close()

# 9. Reports
with tabs[8]:
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.metric("Total Sales", f"Rs. {pd.read_sql('SELECT SUM(total) FROM sales', conn).iloc[0,0] or 0}")
    st.metric("Total Expenses", f"Rs. {pd.read_sql('SELECT SUM(amount) FROM expenses', conn).iloc[0,0] or 0}")
    conn.close()
