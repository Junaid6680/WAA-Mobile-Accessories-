import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import portrait
import io

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect('waa_mobile_pos.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, cost_price REAL, stock INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, customer_name TEXT, total REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT, balance_receivable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, description TEXT, amount REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS capital (partner TEXT PRIMARY KEY, opening_balance REAL, investment REAL, withdrawals REAL, profit_share REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS returns (id INTEGER PRIMARY KEY, item_name TEXT, qty INTEGER, amount REAL, date TEXT)')
    
    try:
        c.execute("SELECT opening_balance FROM capital LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE capital ADD COLUMN opening_balance REAL DEFAULT 0.0")
    
    conn.commit()
    conn.close()

init_db()

# --- Thermal PDF Function (80mm width) ---
def create_thermal_pdf(customer, items, grand_total):
    # 80mm is approx 226 points. Height is dynamic based on items.
    receipt_width = 226 
    receipt_height = 400 + (len(items) * 20)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=(receipt_width, receipt_height))
    
    # Header
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(113, receipt_height - 30, "WAA AA MOBILE")
    p.setFont("Helvetica", 8)
    p.drawCentredString(113, receipt_height - 45, "Shop T-27, Hall Road, Lahore")
    p.drawCentredString(113, receipt_height - 55, "0304-4724435 | 0303-0075400")
    p.line(10, receipt_height - 65, 216, receipt_height - 65)
    
    # Bill Details
    p.drawString(10, receipt_height - 80, f"Cust: {customer}")
    p.drawString(10, receipt_height - 90, f"Date: {datetime.now().strftime('%d-%m-%y %H:%M')}")
    p.line(10, receipt_height - 100, 216, receipt_height - 100)
    
    # Table Header
    p.setFont("Helvetica-Bold", 8)
    p.drawString(10, receipt_height - 115, "Item")
    p.drawString(130, receipt_height - 115, "Qty")
    p.drawString(180, receipt_height - 115, "Total")
    
    # Items
    y = receipt_height - 130
    p.setFont("Helvetica", 8)
    for item in items:
        name = (item['item'][:18] + '..') if len(item['item']) > 18 else item['item']
        p.drawString(10, y, name)
        p.drawString(135, y, str(item['qty']))
        p.drawString(180, y, str(int(item['total'])))
        y -= 15
    
    # Total
    p.line(10, y, 216, y)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(10, y - 20, f"GRAND TOTAL: Rs. {int(grand_total)}")
    p.setFont("Helvetica", 7)
    p.drawCentredString(113, y - 40, "Thank you for your business!")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- App UI ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if not st.session_state['logged_in']:
    st.sidebar.title("🔐 Login")
    u, p = st.sidebar.text_input("User"), st.sidebar.text_input("Pass", type="password")
    if st.sidebar.button("Login"):
        if u == "admin" and p == "waa123":
            st.session_state['logged_in'] = True
            st.rerun()
    st.stop()

st.title("📱 WAA AA Mobile POS")
tabs = st.tabs(["Invoice", "Customers", "Returns", "Stock", "Capital", "Reports"])

# 1. Invoice
with tabs[0]:
    if 'bill_items' not in st.session_state: st.session_state['bill_items'] = []
    conn = sqlite3.connect('waa_mobile_pos.db')
    custs = pd.read_sql("SELECT name FROM customers", conn)['name'].tolist()
    prods = pd.read_sql("SELECT item_name FROM inventory", conn)
    
    customer = st.selectbox("Select Customer", custs)
    col1, col2, col3 = st.columns([3,1,1])
    with col1: prod = st.selectbox("Product", prods['item_name'])
    with col2: q = st.number_input("Qty", 1)
    with col3: pr = st.number_input("Price", 0.0)
    
    if st.button("Add Item"):
        st.session_state['bill_items'].append({'item': prod, 'qty': q, 'price': pr, 'total': q*pr})
    
    if st.session_state['bill_items']:
        st.table(pd.DataFrame(st.session_state['bill_items']))
        gt = sum(i['total'] for i in st.session_state['bill_items'])
        
        if st.button("Finalize & Print"):
            c = conn.cursor()
            c.execute("INSERT INTO sales (customer_name, total, date) VALUES (?,?,?)", (customer, gt, datetime.now().strftime('%Y-%m-%d')))
            c.execute("UPDATE customers SET balance_receivable = balance_receivable + ? WHERE name = ?", (gt, customer))
            for i in st.session_state['bill_items']:
                c.execute("UPDATE inventory SET stock = stock - ? WHERE item_name = ?", (i['qty'], i['item']))
            conn.commit()
            
            pdf = create_thermal_pdf(customer, st.session_state['bill_items'], gt)
            st.download_button("📥 Download Receipt", pdf, f"Receipt_{customer}.pdf", "application/pdf")
            st.session_state['bill_items'] = []
            st.success("Bill Saved!")
    conn.close()

# 2. Customers
with tabs[1]:
    st.header("Customers")
    name = st.text_input("Customer Name")
    bal = st.number_input("Opening Balance", 0.0)
    if st.button("Add"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("INSERT INTO customers (name, balance_receivable) VALUES (?,?)", (name, bal))
        conn.commit()
        st.rerun()
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM customers", conn), use_container_width=True)
    conn.close()

# 3. Returns
with tabs[2]:
    st.header("Returns")
    conn = sqlite3.connect('waa_mobile_pos.db')
    itms = pd.read_sql("SELECT item_name FROM inventory", conn)['item_name'].tolist()
    r_itm = st.selectbox("Return Item", itms)
    r_q = st.number_input("Return Qty", 1)
    if st.button("Process Return"):
        conn.execute("UPDATE inventory SET stock = stock + ? WHERE item_name = ?", (r_q, r_itm))
        conn.commit()
        st.success("Stock Updated!")
    conn.close()

# 4. Stock
with tabs[3]:
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
    conn.close()

# 5. Capital
with tabs[4]:
    st.header("Capital A/C")
    p_name = st.selectbox("Partner", ["M Waqas", "Farman Ali", "Fareed Ahmed"])
    o_b = st.number_input("Set Opening Balance", 0.0)
    if st.button("Update Opening"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("UPDATE capital SET opening_balance = ? WHERE partner = ?", (o_b, p_name))
        conn.commit()
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT partner, opening_balance, investment, withdrawals FROM capital", conn))
    conn.close()

# 6. Reports
with tabs[5]:
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.metric("Total Sales Today", f"Rs. {pd.read_sql('SELECT SUM(total) FROM sales', conn).iloc[0,0] or 0}")
    conn.close()
