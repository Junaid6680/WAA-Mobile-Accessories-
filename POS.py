import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
import io

# Database Initialization
def init_db():
    conn = sqlite3.connect('waa_mobile_pos.db')
    c = conn.cursor()
    # 1. Inventory Table
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY, item_name TEXT, cost_price REAL, stock INTEGER)''')
    # 2. Sales Table
    c.execute('''CREATE TABLE IF NOT EXISTS sales 
                 (id INTEGER PRIMARY KEY, customer_name TEXT, total REAL, date TEXT)''')
    # 3. Suppliers
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers 
                 (id INTEGER PRIMARY KEY, name TEXT, balance_payable REAL)''')
    # 4. Customers
    c.execute('''CREATE TABLE IF NOT EXISTS customers 
                 (id INTEGER PRIMARY KEY, name TEXT, balance_receivable REAL)''')
    # 5. Expenses
    c.execute('''CREATE TABLE IF NOT EXISTS expenses 
                 (id INTEGER PRIMARY KEY, category TEXT, amount REAL, date TEXT)''')
    # 6. Capital Accounts
    c.execute('''CREATE TABLE IF NOT EXISTS capital 
                 (partner TEXT PRIMARY KEY, investment REAL, profit_share REAL)''')
    
    # --- Testing Data Insertion ---
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        # 15 Testing Items
        items = [('Samsung Charger', 450, 50), ('IPhone Cable', 300, 40), ('Handsfree MI', 150, 100),
                 ('Power Bank', 2500, 10), ('Glass Protector', 50, 200), ('Back Cover', 120, 80),
                 ('Airpods Pro', 1800, 15), ('Memory Card 32GB', 600, 30), ('Battery Nokia', 250, 25),
                 ('Type-C Adapter', 80, 60), ('Car Charger', 350, 20), ('Bluetooth Speaker', 1200, 12),
                 ('Ring Light', 950, 8), ('USB 64GB', 850, 25), ('Selfie Stick', 200, 15)]
        c.executemany("INSERT INTO inventory (item_name, cost_price, stock) VALUES (?,?,?)", items)
        
        # Suppliers
        c.executemany("INSERT INTO suppliers (name, balance_payable) VALUES (?,?)", [('ABC Accessories', 50000), ('Hall Road Wholesaler', 25000)])
        
        # Customers
        c.executemany("INSERT INTO customers (name, balance_receivable) VALUES (?,?)", [('Aslam Mobile', 1200), ('Khan Communication', 5000), ('City Shop', 3400)])
        
        # Partners Capital
        for partner in ['M Waqas', 'Farid Khan', 'Farman Ali']:
            c.execute("INSERT INTO capital (partner, investment, profit_share) VALUES (?,?,?)", (partner, 0.0, 0.0))
            
    conn.commit()
    conn.close()

init_db()

# --- Utility: PDF Generator ---
def generate_pdf(bill_data):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "WAA AA Mobile Accessories - Invoice")
    p.drawString(100, 780, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    p.drawString(100, 760, "------------------------------------")
    y = 740
    for item in bill_data:
        p.drawString(100, y, f"{item['name']} x {item['qty']} = {item['total']}")
        y -= 20
    p.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI ---
st.set_page_config(page_title="WAA AA Mobile POS", layout="wide")
st.title("📱 WAA AA Mobile Accessories")
st.write("Shop T-27, 3rd Floor, Hassan Center 2, Hall Road, Lahore.")

tabs = st.tabs(["Invoice/Billing", "Inventory", "Suppliers", "Customers", "Expenses", "Capital A/C", "Purchase/Return", "Reports"])

# 1. Invoice
with tabs[0]:
    st.header("Generate Invoice")
    conn = sqlite3.connect('waa_mobile_pos.db')
    items = pd.read_sql("SELECT item_name, cost_price FROM inventory", conn)
    c_name = st.text_input("Customer Name")
    selected_item = st.selectbox("Select Product", items['item_name'])
    qty = st.number_input("Quantity", min_value=1)
    sale_price = st.number_input("Sale Price (Apni Marzi Ki)", min_value=0.0)
    
    if st.button("Add to Bill & Print PDF"):
        total = sale_price * qty
        bill_info = [{"name": selected_item, "qty": qty, "total": total}]
        pdf = generate_pdf(bill_info)
        st.download_button("Download Bill PDF", data=pdf, file_name="bill.pdf", mime="application/pdf")
        st.success(f"Total Bill: {total}")

# 2. Inventory
with tabs[1]:
    st.header("Stock Management")
    conn = sqlite3.connect('waa_mobile_pos.db')
    df_inv = pd.read_sql("SELECT * FROM inventory", conn)
    st.dataframe(df_inv, use_container_width=True)

# 3. Suppliers
with tabs[2]:
    st.header("Supplier Balances")
    conn = sqlite3.connect('waa_mobile_pos.db')
    df_sup = pd.read_sql("SELECT * FROM suppliers", conn)
    st.table(df_sup)

# 4. Customers
with tabs[3]:
    st.header("Customer Dues")
    conn = sqlite3.connect('waa_mobile_pos.db')
    df_cust = pd.read_sql("SELECT * FROM customers", conn)
    st.table(df_cust)

# 5. Shop Expense
with tabs[4]:
    st.header("Daily Expenses")
    exp_cat = st.selectbox("Category", ["Rent", "Electricity", "Tea/Food", "Other"])
    exp_amt = st.number_input("Amount", min_value=0.0)
    if st.button("Add Expense"):
        conn = sqlite3.connect('waa_mobile_pos.db')
        conn.execute("INSERT INTO expenses (category, amount, date) VALUES (?,?,?)", (exp_cat, exp_amt, datetime.now().date()))
        conn.commit()
        st.success("Expense Added")

# 6. Capital Account
with tabs[5]:
    st.header("Partners Capital & Profit")
    conn = sqlite3.connect('waa_mobile_pos.db')
    # Yahan investment update karne ka option
    partner = st.selectbox("Select Partner", ["M Waqas", "Farid Khan", "Farman Ali"])
    amount = st.number_input("Add Investment", min_value=0.0)
    if st.button("Update Capital"):
        conn.execute("UPDATE capital SET investment = investment + ? WHERE partner = ?", (amount, partner))
        conn.commit()
    df_cap = pd.read_sql("SELECT * FROM capital", conn)
    st.dataframe(df_cap)

# 7. Purchase/Return
with tabs[6]:
    st.header("Stock Purchase / Returns")
    st.info("Yahan se aap naya maal purchase ya return record kar sakte hain.")

# 8. Reports
with tabs[7]:
    st.header("Business Reports")
    rep_type = st.radio("Select Type", ["Daily", "Weekly", "Monthly", "Yearly"])
    st.write(f"Displaying {rep_type} Report...")
    # Reports logic filters data based on date
