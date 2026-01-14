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

# Tables Create Karein
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT, bank_name TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS expenses(date TEXT, title TEXT, amount INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
conn.commit()

# --- 15 SAMPLE ITEMS ADD KARNA ---
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

# --- 5 PERMANENT CUSTOMERS ADD KARNA ---
customers_list = [
    ("Junaid Mobile Hall Road", 15000),
    ("Ali Accessories Lahore", 8500),
    ("Zubair Communication", 22000),
    ("Hamza Smart Shop", 5000),
    ("Bilal Electronics", 12000)
]
for name, bal in customers_list:
    c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (name, bal))
conn.commit()

# ---------- HEADER ----------
st.title("🏬 WAA Mobile Accessories")
st.markdown("---")

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "👥 Customers & Khata", "💰 Receiving", "📊 Reports"])

# ================= 1. SALE INVOICE =================
with tabs[0]:
    st.subheader("New Sale")
    cust_query = c.execute("SELECT name FROM customers").fetchall()
    cust_list = ["Walk-in"] + [r[0] for r in cust_query]
    
    col1, col2 = st.columns(2)
    with col1: 
        selected_cust = st.selectbox("Select Customer", cust_list)
        final_customer = st.text_input("Enter Name", value="Walk-in Customer") if selected_cust == "Walk-in" else selected_cust
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
        if st.button("💾 Save Bill & Update Credit"):
            bill_total = df_cart["Total"].sum()
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (inv_no, s_date.strftime("%Y-%m-%d"), final_customer, bill_total))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            st.session_state.cart = []
            st.success(f"Bill #{inv_no} Saved! Total: Rs {bill_total}")
            st.rerun()

# ================= 2. CUSTOMERS & KHATA =================
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
        ledger_list.append({"Customer": name, "Opening Balance": old_bal, "Total Sales": sales, "Total Paid": paid, "Balance Due": balance})
    
    if ledger_list:
        st.table(pd.DataFrame(ledger_list))

# ================= 3. RECEIVING =================
with tabs[3]:
    st.subheader("📥 Receive Payment")
    active_custs = list(set([r[0] for r in c.execute("SELECT customer FROM invoices").fetchall()] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]))
    r_cust = st.selectbox("From Customer", active_custs)
    r_amt = st.number_input("Amount", min_value=0)
    r_meth = st.selectbox("Bank/Method", ["Cash", "Meezan Bank", "Faysal Bank", "EasyPaisa", "JazzCash"])
    if st.button("Record Payment"):
        c.execute("INSERT INTO payments VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_cust, r_amt, r_meth, r_meth if "Bank" in r_meth else ""))
        conn.commit()
        st.success("Payment Saved!")
        st.rerun()
