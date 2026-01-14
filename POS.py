import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ---------- CONFIG ----------
st.set_page_config("WAA POS", layout="wide")
DB = "waa_full_pos.db"

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Tables Ensure Karein
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT, bank_name TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
conn.commit()

# --- 15 SAMPLE ITEMS (Automatic Add) ---
items_list = [
    ("iPhone 13 Case", 50, 850), ("iPhone 14 Pro Max Glass", 100, 450),
    ("Samsung 25W Adapter", 30, 2200), ("Type-C to Lightning Cable", 40, 950),
    ("Airpods Pro 2nd Gen", 15, 4800), ("M10 TWS Earbuds", 25, 1250),
    ("65W Super Fast Charger", 20, 3200), ("Micro USB Cable 2m", 60, 350),
    ("Phone Tripod Stand", 10, 1100), ("Power Bank 20000mAh", 12, 5500),
    ("Bluetooth Speaker Mini", 18, 1800), ("Gaming Headset G20", 8, 3500),
    ("Smart Watch Ultra", 15, 4200), ("Magnetic Car Mount", 35, 650),
    ("OTG Adapter Type-C", 80, 250)
]
for name, q, p in items_list:
    c.execute("INSERT OR IGNORE INTO inventory VALUES(?,?,?)", (name, q, p))

# --- 5 PERMANENT CUSTOMERS (Automatic Add) ---
customers_list = [
    ("Junaid Mobile Hall Road", 15000), ("Ali Accessories Lahore", 8500),
    ("Zubair Communication", 22000), ("Hamza Smart Shop", 5000), ("Bilal Electronics", 12000)
]
for name, bal in customers_list:
    c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (name, bal))
conn.commit()

# ---------- HEADER ----------
st.title("🏬 WAA Mobile Accessories")
st.markdown("---")

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory Management", "👥 Customers & Khata", "💰 Receiving", "📊 Reports"])

# ================= 1. SALE INVOICE (Stock Minus Hoga) =================
with tabs[0]:
    st.subheader("New Sale")
    cust_query = c.execute("SELECT name FROM customers").fetchall()
    cust_list = ["Walk-in"] + [r[0] for r in cust_query]
    
    col1, col2 = st.columns(2)
    with col1: 
        selected_cust = st.selectbox("Select Customer", cust_list)
        final_customer = st.text_input("Enter Walk-in Name", value="Walk-in Customer") if selected_cust == "Walk-in" else selected_cust
    with col2: s_date = st.date_input("Date", datetime.now())

    inv_data = pd.read_sql("SELECT * FROM inventory", conn)
    c1, c2 = st.columns(2)
    with c1: itm = st.selectbox("Item", inv_data["item"]) if not inv_data.empty else None
    with c2: q = st.number_input("Qty", min_value=1, value=1)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    if st.button("➕ Add to Cart"):
        p = inv_data.loc[inv_data.item == itm, "price"].values[0]
        st.session_state.cart.append({"Item": itm, "Qty": q, "Price": p, "Total": q*p})
        st.rerun()

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart)
        if st.button("💾 Save Bill (Update Stock & Khata)"):
            bill_total = df_cart["Total"].sum()
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (inv_no, s_date.strftime("%Y-%m-%d"), final_customer, bill_total))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            st.session_state.cart = []
            st.success(f"Bill #{inv_no} Saved! Stock Updated.")
            st.rerun()

# ================= 2. INVENTORY MANAGEMENT (Stock Plus Hoga) =================
with tabs[1]:
    st.subheader("📦 Inventory Stock Control")
    col1, col2, col3 = st.columns(3)
    
    with col1: 
        edit_item = st.selectbox("Select Item to Update Stock", inv_data["item"])
    with col2:
        new_qty = st.number_input("Add New Stock Quantity", min_value=0, value=0)
    with col3:
        if st.button("📥 Add Stock (Purchase)"):
            c.execute("UPDATE inventory SET qty = qty + ? WHERE item = ?", (new_qty, edit_item))
            conn.commit()
            st.success(f"{new_qty} units added to {edit_item}")
            st.rerun()
    
    st.write("### 📊 Current Stock Status")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# ================= 3. CUSTOMERS & KHATA =================
with tabs[2]:
    st.subheader("📜 Running Ledger (Udhaar Hisab)")
    all_c = pd.read_sql("SELECT * FROM customers", conn)
    ledger_list = []
    for _, row in all_c.iterrows():
        name = row['name']
        old_bal = row['opening_balance']
        sales = pd.read_sql(f"SELECT SUM(total) FROM invoices WHERE customer='{name}'", conn).iloc[0,0] or 0
        paid = pd.read_sql(f"SELECT SUM(amount) FROM payments WHERE customer='{name}'", conn).iloc[0,0] or 0
        balance = old_bal + sales - paid
        ledger_list.append({"Customer": name, "Old Balance": old_bal, "New Sales": sales, "Total Paid": paid, "Payable": balance})
    
    st.table(pd.DataFrame(ledger_list))
