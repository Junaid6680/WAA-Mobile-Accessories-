import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
import io

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('waa_mobile_pos.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, cost_price REAL, stock INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, customer_name TEXT, total REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY, name TEXT, balance_payable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT, balance_receivable REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, category TEXT, amount REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS capital (partner TEXT PRIMARY KEY, investment REAL, profit_share REAL)')
    
    # Testing Data (if empty)
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        items = [('Samsung Charger', 450, 50), ('IPhone Cable', 300, 40), ('Handsfree MI', 150, 100),
                 ('Power Bank', 2500, 10), ('Glass Protector', 50, 200), ('Back Cover', 120, 80),
                 ('Airpods Pro', 1800, 15), ('Memory Card 32GB', 600, 30), ('Battery Nokia', 250, 25),
                 ('Type-C Adapter', 80, 60), ('Car Charger', 350, 20), ('Bluetooth Speaker', 1200, 12),
                 ('Ring Light', 950, 8), ('USB 64GB', 850, 25), ('Selfie Stick', 200, 15)]
        c.executemany("INSERT INTO inventory (item_name, cost_price, stock) VALUES (?,?,?)", items)
        c.executemany("INSERT INTO suppliers (name, balance_payable) VALUES (?,?)", [('ABC Accessories', 50000), ('Hall Road Wholesaler', 25000)])
        c.executemany("INSERT INTO customers (name, balance_receivable) VALUES (?,?)", [('Aslam Mobile', 1200), ('Khan Communication', 5000), ('City Shop', 3400)])
        for p in ['M Waqas', 'Farid Khan', 'Farman Ali']:
            c.execute("INSERT OR IGNORE INTO capital (partner, investment, profit_share) VALUES (?,?,?)", (p, 0.0, 0.0))
    conn.commit()
    conn.close()

init_db()

# --- PDF Generator ---
def generate_pdf(customer, items_list, grand_total):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, 800, "WAA AA MOBILE ACCESSORIES")
    p.setFont("Helvetica", 10)
    p.drawString(100, 780, "Shop T-27, 3rd Floor, Hassan Center 2, Hall Road, Lahore")
    p.drawString(100, 765, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    p.drawString(100, 750, f"Customer: {customer}")
    p.line(100, 740, 500, 740)
    y = 720
    for item in items_list:
        p.drawString(100, y, f"{item['name']} x {item['qty']} @ {item['price']} = {item['total']}")
        y -= 20
    p.line(100, y, 500, y)
    p.drawString(350, y-20, f"Grand Total: Rs. {grand_total}")
    p.save()
    buffer.seek(0)
    return buffer

# --- Login Function ---
def login():
    st.sidebar.title("🔐 Shop Login")
    user = st.sidebar.text_input("Username")
    pw = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if user == "admin" and pw == "waa123":
            st.session_state['logged_in'] = True
        else:
            st.sidebar.error("Ghalat details!")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    login()
    st.warning("Pehle Login Karein (Sidebar)")
    st.stop()

# --- Main App ---
st.title("📱 WAA AA Mobile POS")
tabs = st.tabs(["Invoice/Billing", "Receiving Payments", "Inventory", "Suppliers", "Customers", "Expenses", "Capital A/C", "Reports"])

# 1. Invoice with Customer Selection
with tabs[0]:
    st.header("New Order / Bill")
    conn = sqlite3.connect('waa_mobile_pos.db')
    cust_df = pd.read_sql("SELECT name FROM customers", conn)
    item_df = pd.read_sql("SELECT item_name FROM inventory", conn)
    
    cust_name = st.selectbox("Select Customer (Save List)", cust_df['name'])
    prod_name = st.selectbox("Select Product", item_df['item_name'])
    qty = st.number_input("Quantity", min_value=1, value=1)
    s_price = st.number_input("Sale Price (Custom)", min_value=0.0)
    
    if st.button("Generate Bill & Update Balance"):
        total = s_price * qty
        c = conn.cursor()
        # Update Sales
        c.execute("INSERT INTO sales (customer_name, total, date) VALUES (?,?,?)", (cust_name, total, datetime.now().date()))
        # Update Customer Balance (Credit sale)
        c.execute("UPDATE customers SET balance_receivable = balance_receivable + ? WHERE name = ?", (total, cust_name))
        # Update Stock
        c.execute("UPDATE inventory SET stock = stock - ? WHERE item_name = ?", (qty, prod_name))
        conn.commit()
        
        pdf = generate_pdf(cust_name, [{"name": prod_name, "qty": qty, "price": s_price, "total": total}], total)
        st.download_button("Download & Print Bill", data=pdf, file_name=f"Bill_{cust_name}.pdf", mime="application/pdf")
        st.success(f"Bill Saved! New Balance for {cust_name} added.")
    conn.close()

# 2. Receiving Payments
with tabs[1]:
    st.header("Receive Payment from Customer")
    conn = sqlite3.connect('waa_mobile_pos.db')
    cust_list = pd.read_sql("SELECT name, balance_receivable FROM customers", conn)
    st.dataframe(cust_list)
    
    selected_c = st.selectbox("Payment kis se aayi?", cust_list['name'])
    amount_rec = st.number_input("Kitni Payment mili?", min_value=0.0)
    
    if st.button("Confirm Payment"):
        c = conn.cursor()
        c.execute("UPDATE customers SET balance_receivable = balance_receivable - ? WHERE name = ?", (amount_rec, selected_c))
        conn.commit()
        st.success(f"Balance updated! {amount_rec} received from {selected_c}")
    conn.close()

# Baki tabs code (Inventory, Suppliers, etc. same as previous request)
with tabs[2]:
    st.header("Stock Management")
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)
    conn.close()

with tabs[4]:
    st.header("Customer List")
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT * FROM customers", conn))
    conn.close()

with tabs[6]:
    st.header("Capital Account (Partners)")
    conn = sqlite3.connect('waa_mobile_pos.db')
    st.table(pd.read_sql("SELECT * FROM capital", conn))
    conn.close()
