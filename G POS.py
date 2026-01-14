import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# ---------- CONFIG ----------
st.set_page_config("WAA POS Ultimate", layout="wide")
DB = "waa_mobile_v5_final.db" # Fresh DB to ensure all fixes work

conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# ---------- DATABASE TABLES ----------
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, cost INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER, total_cost INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS capital(date TEXT, partner TEXT, amount INTEGER, type TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS returns(date TEXT, customer TEXT, item TEXT, qty INTEGER, amount INTEGER)")
conn.commit()

# --- 15 ITEMS WITH COST ---
sample_items = [
    ("iPhone 13 Case", 50, 400), ("iPhone 14 Glass", 100, 150),
    ("Samsung 25W Adapter", 30, 1200), ("Type-C Cable", 40, 300),
    ("Airpods Pro 2", 15, 2500), ("M10 TWS Earbuds", 25, 650),
    ("65W Fast Charger", 20, 1800), ("Micro USB Cable", 60, 120),
    ("Phone Tripod", 10, 500), ("Power Bank 20k", 12, 3500),
    ("Mini Speaker", 18, 900), ("Gaming Headset", 8, 2200),
    ("Smart Watch Ultra", 15, 2800), ("Car Mount", 35, 250),
    ("OTG Adapter", 80, 80)
]
for name, q, cost in sample_items:
    c.execute("INSERT OR IGNORE INTO inventory (item, qty, cost) VALUES(?,?,?)", (name, q, cost))
conn.commit()

# ---------- APP TABS ----------
tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "👥 Customers Ledger", "💰 Cash Book", "🤝 Capital Account", "🔄 Returns", "📊 Business Reports"])

# 1. SALE INVOICE (With Total Fix)
with tabs[0]:
    st.subheader("Create Invoice")
    c_names = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    cust_sel = st.selectbox("Select Customer", c_names)
    
    inv_data = pd.read_sql("SELECT * FROM inventory", conn)
    col1, col2, col3 = st.columns(3)
    with col1: sel_item = st.selectbox("Item", inv_data['item'])
    with col2: sel_qty = st.number_input("Qty", 1)
    with col3: sel_rate = st.number_input("Sale Rate", 0)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    
    if st.button("➕ Add to Cart"):
        item_cost = inv_data.loc[inv_data.item == sel_item, 'cost'].values[0]
        st.session_state.cart.append({"Item": sel_item, "Qty": sel_qty, "Cost": item_cost, "Rate": sel_rate, "Total": sel_qty*sel_rate})
        st.rerun()

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart[['Item', 'Qty', 'Rate', 'Total']])
        
        grand_total = df_cart['Total'].sum()
        grand_cost = (df_cart['Cost'] * df_cart['Qty']).sum()
        
        st.markdown(f"### 🏷️ Total Amount: Rs {grand_total}")
        
        if st.button("💾 Finalize & Save Bill"):
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?,?)", (inv_no, datetime.now().strftime("%Y-%m-%d"), cust_sel, grand_total, grand_cost))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            st.session_state.cart = []
            st.success(f"Bill #{inv_no} Saved! Ledger Updated.")
            st.rerun()

# 2. INVENTORY
with tabs[1]:
    st.subheader("Current Inventory")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# 3. CUSTOMER LEDGER (Fixed Payable Issue)
with tabs[2]:
    st.subheader("📜 Running Ledger")
    with st.expander("Add New Customer"):
        nc, ob = st.text_input("Name"), st.number_input("Opening Balance", 0)
        if st.button("Save"):
            c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (nc, ob))
            conn.commit(); st.rerun()

    cust_df = pd.read_sql("SELECT * FROM customers", conn)
    ledger = []
    for _, r in cust_df.iterrows():
        name = r['name']
        s = pd.read_sql("SELECT SUM(total) FROM invoices WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        p = pd.read_sql("SELECT SUM(amount) FROM payments WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        rt = pd.read_sql("SELECT SUM(amount) FROM returns WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        ledger.append({"Customer": name, "Old Bal": r['opening_balance'], "Sales(+)": s, "Paid/Ret(-)": p+rt, "Payable": r['opening_balance']+s-p-rt})
    st.table(pd.DataFrame(ledger))

# 4. CAPITAL ACCOUNT (Fixed Option)
with tabs[4]:
    st.subheader("🤝 Partner Investment")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_name = st.selectbox("Partner", ["M Waqas", "Farid Khan", "Farman Ali"])
        p_amt = st.number_input("Amount", 0, key="p_amt")
        p_type = st.selectbox("Entry Type", ["Investment (Add)", "Withdrawal (Take Out)"])
        if st.button("Save Entry"):
            c.execute("INSERT INTO capital VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), p_name, p_amt, p_type))
            conn.commit(); st.success("Done!"); st.rerun()
    with col_p2:
        st.write("Recent Entries:")
        st.dataframe(pd.read_sql("SELECT * FROM capital ORDER BY date DESC", conn))

# 5. RETURNS
with tabs[5]:
    st.subheader("🔄 Stock Returns")
    ret_c = st.selectbox("Select Customer ", c_names, key="ret_c")
    ret_i = st.selectbox("Select Item ", [r[0] for r in c.execute("SELECT item FROM inventory").fetchall()], key="ret_i")
    ret_q = st.number_input("Qty", 1, key="ret_q")
    ret_v = st.number_input("Value", 0, key="ret_v")
    if st.button("Process Return"):
        c.execute("INSERT INTO returns VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), ret_c, ret_i, ret_q, ret_v))
        c.execute("UPDATE inventory SET qty = qty + ? WHERE item = ?", (ret_q, ret_i))
        conn.commit(); st.success("Return Recorded!"); st.rerun()

# 6. BUSINESS REPORTS (New)
with tabs[6]:
    st.subheader("📊 Profit & Sales Report")
    total_sales = pd.read_sql("SELECT SUM(total) FROM invoices", conn).iloc[0,0] or 0
    total_cost = pd.read_sql("SELECT SUM(total_cost) FROM invoices", conn).iloc[0,0] or 0
    total_profit = total_sales - total_cost
    
    r1, r2, r3 = st.columns(3)
    r1.metric("Total Sales", f"Rs {total_sales}")
    r2.metric("Gross Profit", f"Rs {total_profit}", delta_color="normal")
    r3.metric("Inventory Value (at Cost)", f"Rs {pd.read_sql('SELECT SUM(qty*cost) FROM inventory', conn).iloc[0,0] or 0}")
