import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# ---------- CONFIG ----------
st.set_page_config("WAA POS Ultimate", layout="wide")
DB = "waa_pos_final_v4.db" # Database name updated for fresh start

# Login Credentials
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Tables setup
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, cost INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER, total_cost INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS suppliers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS capital(date TEXT, partner TEXT, amount INTEGER, type TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS returns(date TEXT, customer TEXT, item TEXT, qty INTEGER, amount INTEGER)")
conn.commit()

# --- 15 SAMPLE ITEMS WITH COST (Automatic Addition) ---
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

# ---------- LOGIN SYSTEM ----------
if "login" not in st.session_state: st.session_state.login = False
if not st.session_state.login:
    st.title("🔐 WAA POS Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.login = True
            st.rerun()
        else: st.error("Ghalt Username ya Password!")
    st.stop()

# ---------- PDF GENERATOR FUNCTION ----------
def generate_bill_pdf(inv_no, customer, date, items_df, total):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "WAA Mobile Accessories", ln=True, align='C')
    pdf.set_font("Arial", size=8)
    pdf.cell(0, 5, f"Bill No: {inv_no}", ln=True)
    pdf.cell(0, 5, f"Date: {date}", ln=True)
    pdf.cell(0, 5, f"Customer: {customer}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(35, 5, "Item")
    pdf.cell(10, 5, "Qty")
    pdf.cell(20, 5, "Total", ln=True)
    pdf.set_font("Arial", size=8)
    for _, row in items_df.iterrows():
        pdf.cell(35, 5, str(row['Item']))
        pdf.cell(10, 5, str(row['Qty']))
        pdf.cell(20, 5, str(row['Total']), ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Total Amount: Rs {total}", ln=True, align='R')
    return pdf.output(dest='S')

# ---------- MAIN APP TABS ----------
tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "👥 Customers Ledger", "💰 Cash Book", "🤝 Capital Account", "🔄 Returns"])

# 1. SALE INVOICE
with tabs[0]:
    st.subheader("New Sale")
    c_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    cust_sel = st.selectbox("Select Customer", c_list)
    final_cust = st.text_input("Customer Name (for Walk-in)", value="Walk-in") if cust_sel == "Walk-in" else cust_sel
    
    inv_data = pd.read_sql("SELECT * FROM inventory", conn)
    col1, col2, col3 = st.columns(3)
    with col1: sel_item = st.selectbox("Item", inv_data['item'])
    with col2: sel_qty = st.number_input("Qty", min_value=1, value=1)
    with col3: sel_rate = st.number_input("Sale Rate (Unit Price)", min_value=0)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    if st.button("➕ Add to Cart"):
        item_cost = inv_data.loc[inv_data.item == sel_item, 'cost'].values[0]
        st.session_state.cart.append({"Item": sel_item, "Qty": sel_qty, "Cost": item_cost, "Rate": sel_rate, "Total": sel_qty*sel_rate})
        st.rerun()

    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.table(cart_df[['Item', 'Qty', 'Rate', 'Total']])
        g_total = cart_df['Total'].sum()
        g_cost = (cart_df['Cost'] * cart_df['Qty']).sum()
        
        if st.button("💾 Save & Generate Bill"):
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?,?)", (inv_no, datetime.now().strftime("%Y-%m-%d"), final_cust, g_total, g_cost))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            
            pdf_bytes = generate_bill_pdf(inv_no, final_cust, datetime.now().strftime("%Y-%m-%d"), cart_df, g_total)
            st.download_button("📥 Click to Download Bill", data=pdf_bytes, file_name=f"WAA_Bill_{inv_no}.pdf", mime="application/pdf")
            st.session_state.cart = []
            st.success("Sale Recorded & Stock Updated!")

# 2. INVENTORY
with tabs[1]:
    st.subheader("Stock Management")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# 3. CUSTOMERS LEDGER
with tabs[2]:
    st.subheader("Running Ledger (Udhaar Hisab)")
    with st.expander("➕ Register New Customer"):
        new_c = st.text_input("Customer Name")
        new_b = st.number_input("Opening Balance", 0)
        if st.button("Add"):
            c.execute("INSERT OR IGNORE INTO customers VALUES(?,?)", (new_c, new_b))
            conn.commit()
            st.rerun()
            
    # Calculation Logic
    all_custs = pd.read_sql("SELECT * FROM customers", conn)
    ledger_list = []
    for _, r in all_custs.iterrows():
        name = r['name']
        sl = pd.read_sql("SELECT SUM(total) FROM invoices WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        pd_amt = pd.read_sql("SELECT SUM(amount) FROM payments WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        rt_amt = pd.read_sql("SELECT SUM(amount) FROM returns WHERE customer=?", conn, params=(name,)).iloc[0,0] or 0
        ledger_list.append({"Customer": name, "Old Bal": r['opening_balance'], "New Sales(+)": sl, "Paid/Returns(-)": pd_amt+rt_amt, "Payable": r['opening_balance']+sl-pd_amt-rt_amt})
    st.dataframe(pd.DataFrame(ledger_list), use_container_width=True)

# 4. CASH BOOK
with tabs[3]:
    st.subheader("💰 Live Balances")
    c_in = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Cash'", conn).iloc[0,0] or 0
    m_bk = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Meezan Bank'", conn).iloc[0,0] or 0
    f_bk = pd.read_sql("SELECT SUM(amount) FROM payments WHERE method='Faysal Bank'", conn).iloc[0,0] or 0
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Cash", f"Rs {c_in}")
    col_b.metric("Meezan", f"Rs {m_bk}")
    col_c.metric("Faysal", f"Rs {f_bk}")
    
    st.divider()
    st.write("### Record Payment")
    r_cust = st.selectbox("From Customer", c_list, key="rec_c")
    r_amt = st.number_input("Amount", 0, key="rec_a")
    r_meth = st.selectbox("Bank/Method", ["Cash", "Meezan Bank", "Faysal Bank"], key="rec_m")
    if st.button("Save Payment"):
        c.execute("INSERT INTO payments VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_cust, r_amt, r_meth))
        conn.commit()
        st.success("Ledger Updated!")
        st.rerun()

# 5. CAPITAL & RETURNS (Simplified)
with tabs[4]:
    st.subheader("Partners Capital")
    p_n = st.selectbox("Partner", ["M Waqas", "Farid Khan", "Farman Ali"])
    p_a = st.number_input("Amount", 0)
    p_t = st.selectbox("Type", ["Investment", "Withdrawal"])
    if st.button("Record Capital"):
        c.execute("INSERT INTO capital VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), p_n, p_a, p_t))
        conn.commit()
        st.rerun()
