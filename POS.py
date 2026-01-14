# WAA_POS_Pro_v6_2026.py
# Complete POS system - DuplicateElementId fixed with unique keys

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ───────────────────────────────────────────────
#                  PAGE CONFIG
# ───────────────────────────────────────────────
st.set_page_config(
    page_title="WAA POS Pro",
    page_icon="🛒",
    layout="wide"
)

# ───────────────────────────────────────────────
#                  DATABASE
# ───────────────────────────────────────────────
DB = "waa_pos_pro_v6.db"

@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(DB, check_same_thread=False)
    return conn

conn = get_db_connection()
c = conn.cursor()

# Create tables
c.executescript('''
CREATE TABLE IF NOT EXISTS inventory(
    item TEXT PRIMARY KEY,
    qty INTEGER DEFAULT 0,
    cost INTEGER DEFAULT 0,
    sale_price INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS invoices(
    inv_no INTEGER PRIMARY KEY,
    date TEXT,
    customer TEXT,
    gross INTEGER,
    discount INTEGER DEFAULT 0,
    net INTEGER,
    total_cost INTEGER
);

CREATE TABLE IF NOT EXISTS customers(
    name TEXT PRIMARY KEY,
    opening_balance INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS suppliers(
    name TEXT PRIMARY KEY,
    opening_balance INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payments(
    date TEXT,
    customer TEXT,
    amount INTEGER,
    method TEXT
);

CREATE TABLE IF NOT EXISTS capital(
    date TEXT,
    partner TEXT,
    amount INTEGER,
    type TEXT CHECK(type IN ('Investment','Withdrawal'))
);

CREATE TABLE IF NOT EXISTS returns(
    date TEXT,
    customer TEXT,
    item TEXT,
    qty INTEGER,
    amount INTEGER
);
''')
conn.commit()

# Sample Items
sample_items = [
    ("iPhone 14 Pro Glass", 120, 280, 650),
    ("Type-C Cable 2m Fast", 180, 150, 380),
    ("65W PD Charger", 55, 1250, 2400),
    ("Airpods Pro 2 Copy", 28, 1800, 3990),
    ("Power Bank 10000mAh", 35, 1450, 2800),
    ("Car Phone Holder", 90, 280, 750),
    ("OTG Adapter", 200, 60, 180),
    ("Back Cover Samsung A14", 95, 320, 850),
]
for it in sample_items:
    c.execute('INSERT OR IGNORE INTO inventory (item, qty, cost, sale_price) VALUES (?,?,?,?)', it)
conn.commit()

# ───────────────────────────────────────────────
#               SESSION STATE
# ───────────────────────────────────────────────
if "cart" not in st.session_state:
    st.session_state.cart = []
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ───────────────────────────────────────────────
#                    LOGIN
# ───────────────────────────────────────────────
if not st.session_state.logged_in:
    st.title("🔐 WAA POS Pro - Login")
    col1, col2, col3 = st.columns([2,3,2])
    with col2:
        u = st.text_input("Username", "admin", key="login_username")
        p = st.text_input("Password", type="password", value="1234", key="login_password")
        if st.button("Login →", type="primary"):
            if u == "admin" and p == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Wrong credentials!")
    st.stop()

# ───────────────────────────────────────────────
#                  MAIN TABS
# ───────────────────────────────────────────────
st.title("🛍️ WAA POS Pro - Mobile Accessories")

tab_sale, tab_inventory, tab_customers, tab_suppliers, tab_payments, tab_capital, tab_returns, tab_reports = st.tabs([
    "🧾 Sale Invoice",
    "📦 Inventory",
    "👥 Customers Ledger",
    "🚚 Suppliers Khata",
    "💰 Payments",
    "🤝 Capital Account",
    "🔄 Returns",
    "📊 Reports"
])

# ── SALE INVOICE ───────────────────────────────────────────
with tab_sale:
    st.subheader("New Sale Invoice")
    
    customers_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    customer = st.selectbox("Customer", customers_list, key="sale_customer_select")
    
    col1, col2 = st.columns([4, 2])
    with col1:
        search = st.text_input("Search Item", placeholder="Type name or leave empty for all...", key="sale_item_search")
    with col2:
        qty = st.number_input("Quantity", min_value=1, value=1, key="sale_quantity")
    
    # Show all if empty search
    if search.strip() == "":
        items_df = pd.read_sql_query("SELECT item, qty, sale_price FROM inventory ORDER BY item LIMIT 100", conn)
    else:
        items_df = pd.read_sql_query("SELECT item, qty, sale_price FROM inventory WHERE item LIKE ? ORDER BY item LIMIT 50", 
                                    conn, params=(f"%{search}%",))
    
    if not items_df.empty:
        options = [f"{r['item']}  (Stock: {r['qty']}) → Rs {r['sale_price']:,}" for _, r in items_df.iterrows()]
        selected = st.radio("Select Item", options, index=None, key="sale_item_radio")
        
        if selected and st.button("➕ Add to Cart", type="primary"):
            item_name = selected.split("  (")[0]
            item_row = items_df[items_df['item'] == item_name].iloc[0]
            
            if qty > item_row['qty']:
                st.error(f"Only {item_row['qty']} available!")
            else:
                st.session_state.cart.append({
                    "item": item_name,
                    "qty": qty,
                    "rate": item_row['sale_price'],
                    "amount": qty * item_row['sale_price']
                })
                st.rerun()
    else:
        st.info("No items found")

    if st.session_state.cart:
        st.divider()
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df, hide_index=True)
        
        gross = cart_df['amount'].sum()
        discount = st.number_input("Discount (Rs)", 0, gross, 0, step=50, key="sale_discount")
        net = gross - discount
        
        st.markdown(f"**Gross:** Rs {gross:,}   |   **Discount:** Rs {discount:,}")
        st.markdown(f"**NET TOTAL:** Rs **{net:,}**")
        
        if st.button("💾 Save & Finalize Bill", type="primary"):
            last_inv = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0]
            inv_no = (last_inv or 999) + 1
            
            date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
            total_cost = sum(it['qty'] * (c.execute("SELECT cost FROM inventory WHERE item=?", (it['item'],)).fetchone()[0] or 0) 
                            for it in st.session_state.cart)
            
            c.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?)",
                     (inv_no, date_now, customer, gross, discount, net, total_cost))
            
            for item in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (item['qty'], item['item']))
            
            conn.commit()
            st.session_state.cart = []
            st.success(f"Bill #{inv_no} Saved!")
            st.balloons()

# ── INVENTORY ──────────────────────────────────────────────
with tab_inventory:
    st.subheader("Current Stock")
    st.dataframe(pd.read_sql("SELECT * FROM inventory ORDER BY item", conn), use_container_width=True)

# ── CUSTOMERS LEDGER ───────────────────────────────────────
with tab_customers:
    st.subheader("Customers Udhaar Ledger")
    
    with st.expander("Add New Customer"):
        cn = st.text_input("Customer Name", key="add_customer_name")
        ob = st.number_input("Opening Balance", value=0, key="add_customer_opening_balance")
        if st.button("Add Customer") and cn:
            c.execute("INSERT OR IGNORE INTO customers VALUES (?,?)", (cn, ob))
            conn.commit()
            st.rerun()
    
    cust_df = pd.read_sql("SELECT * FROM customers", conn)
    ledger_data = []
    for _, row in cust_df.iterrows():
        name = row['name']
        sales = pd.read_sql("SELECT SUM(net) FROM invoices WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        paid = pd.read_sql("SELECT SUM(amount) FROM payments WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        rets = pd.read_sql("SELECT SUM(amount) FROM returns WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        balance = row['opening_balance'] + sales - paid - rets
        ledger_data.append({
            "Customer": name,
            "Opening": row['opening_balance'],
            "Sales": sales,
            "Paid/Return": paid + rets,
            "Balance": balance
        })
    st.dataframe(pd.DataFrame(ledger_data), use_container_width=True)

# ── SUPPLIERS ──────────────────────────────────────────────
with tab_suppliers:
    st.subheader("Suppliers Khata")
    
    with st.expander("Add Supplier"):
        sn = st.text_input("Supplier Name", key="add_supplier_name")
        sob = st.number_input("Opening Balance", value=0, key="add_supplier_opening_balance")
        if st.button("Add Supplier") and sn:
            c.execute("INSERT OR IGNORE INTO suppliers VALUES (?,?)", (sn, sob))
            conn.commit()
            st.rerun()
    
    st.dataframe(pd.read_sql("SELECT * FROM suppliers", conn), use_container_width=True)

# ── PAYMENTS ───────────────────────────────────────────────
with tab_payments:
    st.subheader("Record Customer Payment")
    
    customers = [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    if not customers:
        st.info("No customers added yet.")
    else:
        cust = st.selectbox("Customer", customers, key="payment_customer_select")
        amt = st.number_input("Amount Received (Rs)", 0, step=500, key="payment_amount")
        method = st.selectbox("Receive in", [
            "Cash",
            "EasyPaisa",
            "JazzCash",
            "Faysal Bank",
            "Meezan Bank"
        ], key="payment_method_select")
        
        if st.button("Save Payment") and amt > 0:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("INSERT INTO payments VALUES(?,?,?,?)", (date_str, cust, amt, method))
            conn.commit()
            st.success(f"Rs {amt:,} received from {cust} via {method}")

# ── CAPITAL ACCOUNT ────────────────────────────────────────
with tab_capital:
    st.subheader("Partner Capital Account")
    partner = st.selectbox("Partner", ["M Waqas", "Farid Khan", "Farman Ali"], key="capital_partner")
    amount = st.number_input("Amount", 0, step=1000, key="capital_amount")
    trans_type = st.selectbox("Type", ["Investment", "Withdrawal"], key="capital_type")
    if st.button("Save"):
        c.execute("INSERT INTO capital VALUES(?,?,?,?)",
                 (datetime.now().strftime("%Y-%m-%d %H:%M"), partner, amount, trans_type))
        conn.commit()
        st.success("Saved")

# ── RETURNS ────────────────────────────────────────────────
with tab_returns:
    st.subheader("Sales Return")
    cust_list = [r[0] for r in c.execute("SELECT name FROM customers")]
    if cust_list:
        cust = st.selectbox("Customer", cust_list, key="return_customer")
        item = st.selectbox("Item", [r[0] for r in c.execute("SELECT item FROM inventory")], key="return_item")
        qty = st.number_input("Quantity", 1, key="return_quantity")
        amt = st.number_input("Return Amount", 0, key="return_amount")
        if st.button("Process"):
            dt = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("INSERT INTO returns VALUES(?,?,?,?,?)", (dt, cust, item, qty, amt))
            c.execute("UPDATE inventory SET qty = qty + ? WHERE item = ?", (qty, item))
            conn.commit()
            st.success("Return processed")

# ── REPORTS ────────────────────────────────────────────────
with tab_reports:
    st.subheader("Business Overview")
    sales = pd.read_sql("SELECT SUM(net) FROM invoices", conn).iloc[0,0] or 0
    costs = pd.read_sql("SELECT SUM(total_cost) FROM invoices", conn).iloc[0,0] or 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales", f"Rs {sales:,}")
    col2.metric("Total Cost", f"Rs {costs:,}")
    col3.metric("Profit", f"Rs {sales - costs:,}")

st.sidebar.caption("WAA POS Pro • v6 • Duplicate ID fixed • 2026")
