# WAA_POS_Pro_v2026.py
# Complete single-file POS system for mobile accessories shop
# Run with: streamlit run WAA_POS_Pro_v2026.py

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# ───────────────────────────────────────────────
#                  PAGE CONFIG
# ───────────────────────────────────────────────
st.set_page_config(
    page_title="WAA POS Pro",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ───────────────────────────────────────────────
#                  DATABASE SETUP
# ───────────────────────────────────────────────
DB = "waa_pos_pro.db"

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB, check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

# Create tables if not exist
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

CREATE TABLE IF NOT EXISTS invoice_items(
    inv_no INTEGER,
    item TEXT,
    qty INTEGER,
    rate INTEGER,
    amount INTEGER
);

CREATE TABLE IF NOT EXISTS customers(
    name TEXT PRIMARY KEY,
    opening_balance INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payments(
    date TEXT,
    customer TEXT,
    amount INTEGER,
    method TEXT
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

# ───────────────────────────────────────────────
#               SAMPLE DATA (first run only)
# ───────────────────────────────────────────────
sample_items = [
    ("iPhone 14 Pro Glass", 85, 280, 650),
    ("Type-C Cable 3m", 120, 180, 450),
    ("65W PD Charger", 45, 1450, 2800),
    ("Airpods Pro 2 Copy", 22, 1950, 4200),
    ("Power Bank 20000mAh", 18, 2850, 5200),
    ("Phone Holder Car", 65, 220, 650),
    ("OTG Adapter", 140, 60, 180),
    ("Back Cover iPhone 13", 70, 350, 950),
]

for item in sample_items:
    c.execute('''
    INSERT OR IGNORE INTO inventory 
    (item, qty, cost, sale_price) VALUES (?,?,?,?)
    ''', item)
conn.commit()

# ───────────────────────────────────────────────
#                   SESSION STATE
# ───────────────────────────────────────────────
if "cart" not in st.session_state:
    st.session_state.cart = []
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ───────────────────────────────────────────────
#                    LOGIN
# ───────────────────────────────────────────────
if not st.session_state.logged_in:
    st.title("🔐 WAA POS Login")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("Username", value="admin")
        password = st.text_input("Password", type="password", value="1234")
        if st.button("Login", type="primary", use_container_width=True):
            if username == "admin" and password == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Incorrect username or password")
    st.stop()

# ───────────────────────────────────────────────
#                    SIDEBAR
# ───────────────────────────────────────────────
with st.sidebar:
    st.title("WAA POS Pro")
    st.caption(f"Date: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
    
    page = st.radio("Main Menu", [
        "🧾 New Sale",
        "📦 Inventory",
        "👥 Customers & Ledger",
        "💰 Payments Received",
        "🔄 Returns",
        "📊 Reports"
    ])
    
    st.divider()
    if st.button("🚪 Logout", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.cart = []
        st.rerun()

# ───────────────────────────────────────────────
#                    PAGES
# ───────────────────────────────────────────────

if page == "🧾 New Sale":
    st.header("New Sale Invoice")
    
    customers = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    customer = st.selectbox("Customer", customers)
    
    # Search & Add items
    col1, col2, col3 = st.columns([4,2,2])
    with col1:
        search = st.text_input("Search item (name)", "")
    with col2:
        qty = st.number_input("Quantity", min_value=1, value=1, step=1)
    with col3:
        st.write("")  # spacer
    
    if search:
        df = pd.read_sql_query(
            "SELECT item, qty, cost, sale_price FROM inventory WHERE item LIKE ? ORDER BY item",
            conn, params=(f"%{search}%",)
        )
        
        if not df.empty:
            choice = st.radio(
                "Select Product",
                [f"{row.item}  |  Stock: {row.qty}  |  Rs {row.sale_price:,}" for _, row in df.iterrows()],
                key="item_choice"
            )
            
            if choice:
                selected_item = choice.split("  |  ")[0]
                item_data = df[df.item == selected_item].iloc[0]
                
                if st.button("➕ Add to Cart", type="primary"):
                    if qty > item_data.qty:
                        st.error(f"Only {item_data.qty} available in stock!")
                    else:
                        amount = qty * item_data.sale_price
                        st.session_state.cart.append({
                            "item": selected_item,
                            "qty": qty,
                            "rate": item_data.sale_price,
                            "amount": amount,
                            "cost": item_data.cost
                        })
                        st.success(f"Added {qty}x {selected_item}")
                        st.rerun()
        else:
            st.info("No items found...")

    # Cart display
    if st.session_state.cart:
        st.divider()
        cart_df = pd.DataFrame(st.session_state.cart)
        
        st.subheader("Current Cart")
        st.dataframe(
            cart_df[["item", "qty", "rate", "amount"]].rename(columns={
                "item":"Product", "qty":"Qty", "rate":"Rate", "amount":"Total"
            }),
            hide_index=True,
            use_container_width=True
        )
        
        gross = cart_df["amount"].sum()
        discount = st.number_input("Discount (Rs)", min_value=0, value=0, step=50)
        net_total = gross - discount
        
        colA, colB = st.columns([3,1])
        with colA:
            st.markdown(f"**Gross Amount:**  Rs {gross:,}")
            st.markdown(f"**Discount:**       Rs {discount:,}")
            st.markdown("─" * 30)
            st.markdown(f"**NET TOTAL**       **Rs {net_total:,}**")
        with colB:
            st.write("")
            if st.button("💾 FINALIZE BILL", type="primary", use_container_width=True):
                # Next invoice number
                last = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0]
                inv_no = (last or 999) + 1
                
                date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                total_cost = (cart_df["qty"] * cart_df["cost"]).sum()
                
                # Save header
                c.execute("""
                INSERT INTO invoices 
                (inv_no, date, customer, gross, discount, net, total_cost)
                VALUES (?,?,?,?,?,?,?)
                """, (inv_no, date_str, customer, gross, discount, net_total, total_cost))
                
                # Save items
                for item in st.session_state.cart:
                    c.execute("""
                    INSERT INTO invoice_items 
                    (inv_no, item, qty, rate, amount)
                    VALUES (?,?,?,?,?)
                    """, (inv_no, item["item"], item["qty"], item["rate"], item["amount"]))
                    
                    # Reduce stock
                    c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?",
                             (item["qty"], item["item"]))
                
                conn.commit()
                st.session_state.cart = []
                st.success(f"Bill #{inv_no} saved successfully!")
                st.balloons()
                st.rerun()

elif page == "📦 Inventory":
    st.header("Inventory Management")
    df = pd.read_sql("SELECT * FROM inventory ORDER BY item", conn)
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "👥 Customers & Ledger":
    st.header("Customers & Ledger")
    
    with st.expander("➕ Add New Customer"):
        col1, col2 = st.columns(2)
        with col1: new_name = st.text_input("Customer Name")
        with col2: opening = st.number_input("Opening Balance", value=0)
        if st.button("Add Customer") and new_name:
            c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (new_name, opening))
            conn.commit()
            st.success("Customer added!")
            st.rerun()

    # Ledger view
    customers = pd.read_sql("SELECT name, opening_balance FROM customers", conn)
    ledger = []
    for _, row in customers.iterrows():
        name = row["name"]
        sales = pd.read_sql("SELECT SUM(net) FROM invoices WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        paid = pd.read_sql("SELECT SUM(amount) FROM payments WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        returned = pd.read_sql("SELECT SUM(amount) FROM returns WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        
        balance = row["opening_balance"] + sales - paid - returned
        ledger.append({
            "Customer": name,
            "Opening": row["opening_balance"],
            "Sales": sales,
            "Received/Return": paid + returned,
            "Balance": balance
        })
    
    st.dataframe(pd.DataFrame(ledger), use_container_width=True)

elif page == "💰 Payments Received":
    st.header("Record Payment Received")
    
    customers = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers")]
    cust = st.selectbox("Customer", customers)
    amount = st.number_input("Amount Received", min_value=0, step=500)
    method = st.selectbox("Payment Method", ["Cash", "EasyPaisa", "JazzCash", "Bank Transfer"])
    
    if st.button("Save Payment") and amount > 0:
        c.execute("INSERT INTO payments VALUES(?,?,?,?)",
                 (datetime.now().strftime("%Y-%m-%d %H:%M"), cust, amount, method))
        conn.commit()
        st.success("Payment recorded!")
        st.rerun()

elif page == "🔄 Returns":
    st.header("Process Return")
    
    customers = [r[0] for r in c.execute("SELECT name FROM customers")]
    cust = st.selectbox("Customer", customers)
    items = [r[0] for r in c.execute("SELECT item FROM inventory")]
    item = st.selectbox("Returned Item", items)
    qty = st.number_input("Return Quantity", min_value=1)
    amount = st.number_input("Return Amount (Rs)", min_value=0)
    
    if st.button("Process Return"):
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.execute("INSERT INTO returns VALUES(?,?,?,?,?)", (date_str, cust, item, qty, amount))
        c.execute("UPDATE inventory SET qty = qty + ? WHERE item = ?", (qty, item))
        conn.commit()
        st.success("Return processed - stock updated")
        st.rerun()

elif page == "📊 Reports":
    st.header("Business Reports")
    
    total_sales = pd.read_sql("SELECT SUM(net) FROM invoices", conn).iloc[0,0] or 0
    total_cost = pd.read_sql("SELECT SUM(total_cost) FROM invoices", conn).iloc[0,0] or 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales", f"Rs {total_sales:,}")
    col2.metric("Total Cost", f"Rs {total_cost:,}")
    col3.metric("Gross Profit", f"Rs {total_sales - total_cost:,}", delta_color="normal")
    
    st.divider()
    st.subheader("Last 10 Invoices")
    recent = pd.read_sql("SELECT * FROM invoices ORDER BY inv_no DESC LIMIT 10", conn)
    st.dataframe(recent, hide_index=True, use_container_width=True)

st.sidebar.caption("WAA POS Pro • 2026 • Simple & Fast")
