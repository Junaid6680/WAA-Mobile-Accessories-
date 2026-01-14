# WAA_POS_Pro_v7_2026.py
# Complete POS system with PDF invoice, dynamic rate, ledger fixes, unique keys

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# ───────────────────────────────────────────────
#                  CONFIG & DATABASE
# ───────────────────────────────────────────────
st.set_page_config(page_title="WAA POS Pro", page_icon="🛒", layout="wide")

DB = "waa_pos_pro_v7.db"
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Create tables
c.executescript('''
CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER DEFAULT 0, cost INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER PRIMARY KEY, date TEXT, customer TEXT, gross INTEGER, discount INTEGER DEFAULT 0, net INTEGER, total_cost INTEGER);
CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS suppliers(name TEXT PRIMARY KEY, opening_balance INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT);
CREATE TABLE IF NOT EXISTS capital(date TEXT, partner TEXT, amount INTEGER, type TEXT CHECK(type IN ('Investment','Withdrawal')));
CREATE TABLE IF NOT EXISTS returns(date TEXT, customer TEXT, item TEXT, qty INTEGER, amount INTEGER);
''')
conn.commit()

# Sample data (cost only, no fixed sale price)
sample_items = [
    ("iPhone 14 Glass", 120, 280),
    ("Type-C Cable 2m", 180, 150),
    ("65W Charger", 55, 1250),
    ("Airpods Pro Copy", 28, 1800),
    ("Power Bank 10000", 35, 1450),
    ("Car Phone Holder", 90, 280),
    ("OTG Adapter", 200, 60),
    ("Back Cover Samsung A14", 95, 320),
]
for item in sample_items:
    c.execute('INSERT OR IGNORE INTO inventory (item, qty, cost) VALUES (?,?,?)', item)
conn.commit()

# Session state
if "cart" not in st.session_state: st.session_state.cart = []
if "logged_in" not in st.session_state: st.session_state.logged_in = False

# ───────────────────────────────────────────────
#                    LOGIN
# ───────────────────────────────────────────────
if not st.session_state.logged_in:
    st.title("🔐 WAA POS Pro Login")
    col1, col2, col3 = st.columns([2,3,2])
    with col2:
        u = st.text_input("Username", value="admin", key="login_username")
        p = st.text_input("Password", type="password", value="1234", key="login_password")
        if st.button("Login", type="primary"):
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

tab_sale, tab_inv, tab_cust, tab_supp, tab_pay, tab_cap, tab_ret, tab_rep = st.tabs([
    "🧾 Sale Invoice",
    "📦 Inventory",
    "👥 Customers Ledger",
    "🚚 Suppliers",
    "💰 Payments",
    "🤝 Capital",
    "🔄 Returns",
    "📊 Reports"
])

# ── SALE INVOICE ───────────────────────────────────────────
with tab_sale:
    st.subheader("New Sale Invoice")
    
    cust_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers")]
    customer = st.selectbox("Customer", cust_list, key="sale_customer")
    
    col1, col2, col3 = st.columns([4,2,2])
    with col1:
        search = st.text_input("Search Item (empty = all)", key="sale_search_input")
    with col2:
        qty = st.number_input("Quantity", min_value=1, value=1, key="sale_qty_input")
    with col3:
        rate = st.number_input("Sale Rate (apni marzi)", min_value=0, value=0, key="sale_rate_input")
    
    # Items list
    if search.strip() == "":
        df = pd.read_sql("SELECT item, qty, cost FROM inventory ORDER BY item LIMIT 100", conn)
    else:
        df = pd.read_sql("SELECT item, qty, cost FROM inventory WHERE item LIKE ? ORDER BY item LIMIT 50",
                        conn, params=(f"%{search}%",))
    
    if not df.empty:
        options = [f"{row.item}  (Stock: {row.qty})  Cost: {row.cost}" for _, row in df.iterrows()]
        selected = st.radio("Select Item", options, index=None, key="sale_item_radio")
        
        if selected and st.button("➕ Add to Cart", type="primary"):
            item_name = selected.split("  (")[0]
            row = df[df['item'] == item_name].iloc[0]
            
            if qty > row['qty']:
                st.error(f"Sirf {row['qty']} stock mojood hai!")
            else:
                amount = qty * rate
                st.session_state.cart.append({
                    "item": item_name,
                    "qty": qty,
                    "rate": rate,
                    "amount": amount,
                    "cost": row['cost']
                })
                st.success(f"Added → {qty}x {item_name}")
                st.rerun()
    
    if st.session_state.cart:
        st.divider()
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df[["item", "qty", "rate", "amount"]], hide_index=True, use_container_width=True)
        
        gross = cart_df["amount"].sum()
        discount = st.number_input("Discount (Rs)", 0, gross, 0, key="sale_discount_input")
        net = gross - discount
        
        st.markdown(f"**Gross:** Rs {gross:,}   |   **Discount:** Rs {discount:,}")
        st.markdown(f"**NET TOTAL:** Rs **{net:,}**")
        
        if st.button("💾 Save & Generate Bill", type="primary"):
            last_inv = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0]
            inv_no = (last_inv or 999) + 1
            
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            total_cost = sum(item["qty"] * item["cost"] for item in st.session_state.cart)
            
            # Save invoice
            c.execute("INSERT INTO invoices VALUES(?,?,?,?,?,?,?)",
                     (inv_no, date_str, customer, gross, discount, net, total_cost))
            
            # Reduce stock
            for item in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?",
                         (item["qty"], item["item"]))
            
            conn.commit()
            
            # ── PDF GENERATION ──────────────────────────────────────
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"WAA POS INVOICE #{inv_no}", ln=1, align="C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 8, f"Date: {date_str} | Customer: {customer}", ln=1, align="C")
            pdf.ln(10)
            
            pdf.cell(90, 8, "Item", border=1)
            pdf.cell(30, 8, "Qty", border=1)
            pdf.cell(30, 8, "Rate", border=1)
            pdf.cell(40, 8, "Amount", border=1)
            pdf.ln()
            
            for item in st.session_state.cart:
                pdf.cell(90, 8, item["item"], border=1)
                pdf.cell(30, 8, str(item["qty"]), border=1)
                pdf.cell(30, 8, f"{item['rate']:,}", border=1)
                pdf.cell(40, 8, f"{item['amount']:,}", border=1)
                pdf.ln()
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(150, 10, "Net Total:", 0)
            pdf.cell(40, 10, f"Rs {net:,}", 0, ln=1)
            
            pdf_bytes = io.BytesIO()
            pdf.output(pdf_bytes)
            pdf_bytes.seek(0)
            
            st.session_state.cart = []
            st.success(f"Bill #{inv_no} Saved Successfully!")
            
            st.download_button(
                label="📄 Download PDF Invoice",
                data=pdf_bytes,
                file_name=f"Invoice_{inv_no}.pdf",
                mime="application/pdf"
            )
            st.balloons()

# ── Other tabs (with unique keys) ────────────────────────────────────────

with tab_inv:
    st.subheader("Current Stock")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

with tab_cust:
    st.subheader("Customers Ledger")
    with st.expander("Add New Customer"):
        cn = st.text_input("Customer Name", key="add_cust_name")
        ob = st.number_input("Opening Balance", 0, key="add_cust_opening")
        if st.button("Add Customer") and cn:
            c.execute("INSERT OR IGNORE INTO customers VALUES (?,?)", (cn, ob))
            conn.commit()
            st.rerun()
    
    # Ledger
    custs = pd.read_sql("SELECT * FROM customers", conn)
    ledger = []
    for _, row in custs.iterrows():
        name = row['name']
        sales = pd.read_sql("SELECT SUM(net) FROM invoices WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        paid = pd.read_sql("SELECT SUM(amount) FROM payments WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        rets = pd.read_sql("SELECT SUM(amount) FROM returns WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        balance = row['opening_balance'] + sales - paid - rets
        ledger.append({"Customer": name, "Opening": row['opening_balance'], "Sales": sales, 
                       "Paid/Return": paid + rets, "Balance": balance})
    st.dataframe(pd.DataFrame(ledger), use_container_width=True)

with tab_supp:
    st.subheader("Suppliers Khata")
    with st.expander("Add Supplier"):
        sn = st.text_input("Supplier Name", key="add_supp_name")
        sob = st.number_input("Opening Balance", 0, key="add_supp_opening")
        if st.button("Add") and sn:
            c.execute("INSERT OR IGNORE INTO suppliers VALUES (?,?)", (sn, sob))
            conn.commit()
            st.rerun()
    st.dataframe(pd.read_sql("SELECT * FROM suppliers", conn))

with tab_pay:
    st.subheader("Record Payment")
    custs = [r[0] for r in c.execute("SELECT name FROM customers")]
    if custs:
        cust = st.selectbox("Customer", custs, key="pay_customer")
        amt = st.number_input("Amount Received", 0, step=500, key="pay_amount")
        method = st.selectbox("Method", ["Cash", "EasyPaisa", "JazzCash", "Faysal Bank", "Meezan Bank"], key="pay_method")
        if st.button("Save Payment") and amt > 0:
            c.execute("INSERT INTO payments VALUES(?,?,?,?)",
                     (datetime.now().strftime("%Y-%m-%d %H:%M"), cust, amt, method))
            conn.commit()
            st.success("Payment recorded - Ledger updated")
    else:
        st.info("Add customers first")

# Remaining tabs (Capital, Returns, Reports) - simple version
with tab_cap:
    st.subheader("Capital Account")
    partner = st.selectbox("Partner", ["M Waqas", "Farid Khan", "Farman Ali"], key="cap_partner")
    amt = st.number_input("Amount", 0, step=1000, key="cap_amt")
    ttype = st.selectbox("Type", ["Investment", "Withdrawal"], key="cap_type")
    if st.button("Save"):
        c.execute("INSERT INTO capital VALUES(?,?,?,?)",
                 (datetime.now().strftime("%Y-%m-%d %H:%M"), partner, amt, ttype))
        conn.commit()
        st.success("Recorded")

with tab_ret:
    st.subheader("Returns")
    custs = [r[0] for r in c.execute("SELECT name FROM customers")]
    if custs:
        cust = st.selectbox("Customer", custs, key="ret_cust")
        item = st.selectbox("Item", [r[0] for r in c.execute("SELECT item FROM inventory")], key="ret_item")
        qty = st.number_input("Qty", 1, key="ret_qty")
        amt = st.number_input("Return Amount", 0, key="ret_amt")
        if st.button("Process Return"):
            dt = datetime.now().strftime("%Y-%m-%d %H:%M")
            c.execute("INSERT INTO returns VALUES(?,?,?,?,?)", (dt, cust, item, qty, amt))
            c.execute("UPDATE inventory SET qty = qty + ? WHERE item = ?", (qty, item))
            conn.commit()
            st.success("Return processed")

with tab_rep:
    st.subheader("Reports")
    sales = pd.read_sql("SELECT SUM(net) FROM invoices", conn).iloc[0,0] or 0
    cost = pd.read_sql("SELECT SUM(total_cost) FROM invoices", conn).iloc[0,0] or 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sales", f"Rs {sales:,}")
    col2.metric("Total Cost", f"Rs {cost:,}")
    col3.metric("Profit", f"Rs {sales - cost:,}")

st.sidebar.caption("WAA POS Pro v7 • PDF Invoice • Dynamic Rate • Ledger Fixed • 2026")
