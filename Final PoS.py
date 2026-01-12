import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import os

# ---------- CONFIG ----------
st.set_page_config("WAA POS", layout="wide")

SHOP_NAME = "WAA Mobile Accessories"
SHOP_ADDRESS = "Shop No T27, 3rd Floor, Hassan Center 2, Hall Road Lahore"
SHOP_CONTACT = "M Waqas 03154899075 | Farid Khan 03284080860 | Farman Ali 03030075400"

ADMIN_USER = "admin"
ADMIN_PASS = "1234"
DB = "waa_full_pos.db"

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoice_items(inv_no INTEGER, item TEXT, qty INTEGER, price INTEGER, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS purchases(pur_no INTEGER, date TEXT, supplier TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, party TEXT, type TEXT, method TEXT, amount INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS expenses(date TEXT, title TEXT, amount INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS partner_ledger(date TEXT, partner_name TEXT, type TEXT, amount INTEGER, remarks TEXT)")
conn.commit()

# ---------- AUTO-IMPORT STOCK ----------
def auto_import_stock():
    check = c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    if check == 0:
        initial_stock = [
            ('USB Type-C Cable', 3000, 250), ('Micro-USB Cable', 2500, 200),
            ('Lightning Cable (iPhone)', 1500, 400), ('Wall Charger (5W)', 700, 500),
            ('Wall Charger (Fast Charging)', 500, 700), ('Car Charger', 660, 600),
            ('Power Bank 10000mAh', 300, 1500), ('Power Bank 20000mAh', 250, 3000),
            ('Silicone Case (Universal)', 2000, 150), ('Hard Case (Brand specific)', 1000, 250),
            ('Flip / Wallet Case', 500, 400), ('Tempered Glass (Universal)', 1800, 150),
            ('Full Body Screen Protector', 500, 300), ('Wired Earphones', 1500, 250),
            ('Bluetooth Earbuds', 700, 1200), ('Over-ear Headphones', 300, 2500),
            ('Bluetooth Speaker (Mini)', 250, 1800), ('Smart Watch', 150, 4000),
            ('Fitness Tracker', 300, 2200), ('Selfie Stick', 400, 500),
            ('Tripod Stand', 200, 900), ('Car Phone Holder', 500, 400),
            ('Pop Socket / Phone Grip', 800, 250), ('Rechargeable Battery', 100, 500),
            ('Mobile Repair Toolkit', 50, 1800), ('Replacement LCD / Screen', 40, 3500),
            ('OTG Adapter', 1000, 200), ('Stylus Pen', 300, 300), ('Cleaning Kit', 250, 100)
        ]
        c.executemany("INSERT OR REPLACE INTO inventory VALUES (?, ?, ?)", initial_stock)
        conn.commit()

auto_import_stock()

# ---------- LOGIN ----------
if "login" not in st.session_state: st.session_state.login = False
if not st.session_state.login:
    st.title("🔐 WAA POS Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.login = True
            st.rerun()
        else: st.error("Ghalt Password!")
    st.stop()

# ---------- HEADER ----------
st.markdown(f"<h2 style='text-align:center'>{SHOP_NAME}</h2><p style='text-align:center'>{SHOP_ADDRESS}<br>📞 {SHOP_CONTACT}</p><hr>", unsafe_allow_html=True)

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "🏭 Purchase", "📝 Khata (Ledger)", "💸 Shop Expenses", "🤝 Capital Account", "📊 Business Reports"])

# ================= 1. SALE INVOICE =================
with tabs[0]:
    st.subheader("New Sale")
    customer = st.text_input("Customer Name", value="Walk-in")
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    col1, col2, col3 = st.columns(3)
    with col1: item = st.selectbox("Item Select", inv_df["item"]) if not inv_df.empty else None
    with col2: qty = st.number_input("Qty", min_value=1, value=1)
    
    if "cart_sale" not in st.session_state: st.session_state.cart_sale = []

    if st.button("➕ Add to Cart"):
        if item:
            price = inv_df.loc[inv_df.item==item, "price"].values[0]
            st.session_state.cart_sale.append({"item": item, "qty": qty, "price": price, "total": qty*price})
    
    if st.session_state.cart_sale:
        st.table(pd.DataFrame(st.session_state.cart_sale))
        if st.button("💾 Save Invoice"):
            last_inv = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000
            new_no = last_inv + 1
            total_bill = sum(x['total'] for x in st.session_state.cart_sale)
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (new_no, datetime.now().strftime("%Y-%m-%d"), customer, total_bill))
            for r in st.session_state.cart_sale:
                c.execute("UPDATE inventory SET qty=qty-? WHERE item=?", (r['qty'], r['item']))
            conn.commit()
            
            # --- PDF GENERATION ---
            pdf = FPDF()
            pdf.add_page()
            if os.path.exists("Logo.png"):
                pdf.image("Logo.png", 10, 8, 30)
            
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, SHOP_NAME, ln=True, align="C")
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 5, SHOP_ADDRESS, ln=True, align="C")
            pdf.ln(10)
            pdf.cell(0, 8, f"Invoice #: {new_no} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
            pdf.cell(0, 8, f"Customer: {customer}", ln=True)
            pdf.ln(2)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(2)
            for r in st.session_state.cart_sale:
                pdf.cell(100, 8, f"{r['item']} (x{r['qty']})", 0)
                pdf.cell(0, 8, f"Rs {r['total']}", 0, ln=True, align="R")
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"Total Amount: Rs {total_bill}", ln=True, align="R")
            
            os.makedirs("bills", exist_ok=True)
            file_path = f"bills/Bill_{new_no}.pdf"
            pdf.output(file_path)
            
            st.session_state.cart_sale = []
            st.success("Sale Recorded & Bill Generated!")
            with open(file_path, "rb") as f:
                st.download_button("⬇️ Download Bill PDF", f, file_name=f"Bill_{new_no}.pdf")

# ================= 2. INVENTORY =================
with tabs[1]:
    st.subheader("Current Stock Status")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# ================= 3. PURCHASE =================
with tabs[2]:
    st.subheader("Add Purchase (Stock In)")
    p_item = st.text_input("Item Name")
    p_qty = st.number_input("Purchase Qty", min_value=1, value=1)
    if st.button("Add Stock"):
        c.execute("UPDATE inventory SET qty=qty+? WHERE item=?", (p_qty, p_item))
        conn.commit()
        st.success("Stock updated successfully!")

# ================= 4. KHATA (LEDGER) =================
with tabs[3]:
    st.subheader("Running Khata")
    st.dataframe(pd.read_sql("SELECT customer, SUM(total) as Total_Sale FROM invoices GROUP BY customer", conn))

# ================= 5. SHOP EXPENSES =================
with tabs[4]:
    st.subheader("💸 Shop Running Expenses")
    exp_t = st.text_input("Reason (e.g. Chai, Bijli)")
    exp_a = st.number_input("Amount", min_value=0, value=0)
    if st.button("Save Shop Expense"):
        c.execute("INSERT INTO expenses VALUES(?,?,?)", (datetime.now().strftime("%Y-%m-%d"), exp_t, exp_a))
        conn.commit()
        st.success("Expense recorded!")

# ================= 6. CAPITAL ACCOUNT =================
with tabs[5]:
    st.subheader("🤝 Partners Capital Account")
    p_names = ["M Waqas", "Farid Khan", "Farman Ali"]
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1: sel_partner = st.selectbox("Partner", p_names)
    with col_p2: trans_type = st.selectbox("Action", ["Investment (Paise Lagaye)", "Withdrawal (Shop se nikale)"])
    with col_p3: p_amount = st.number_input("Amount (PKR)", min_value=0, value=0)
    
    if st.button("Record Capital Transaction"):
        c.execute("INSERT INTO partner_ledger VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), sel_partner, trans_type, p_amount, "Capital Update"))
        conn.commit()
        st.success("Capital record updated!")

    st.write("### 💎 Capital Summary")
    p_sum = pd.read_sql("""SELECT partner_name, 
        SUM(CASE WHEN type LIKE 'Investment%' THEN amount ELSE 0 END) as Total_Investment,
        SUM(CASE WHEN type LIKE 'Withdrawal%' THEN amount ELSE 0 END) as Total_Withdrawal
        FROM partner_ledger GROUP BY partner_name""", conn)
    p_sum['Net_Equity'] = p_sum['Total_Investment'] - p_sum['Total_Withdrawal']
    st.table(p_sum)

# ================= 7. REPORTS =================
with tabs[6]:
    st.subheader("📊 Profit/Loss Overview")
    sales = pd.read_sql("SELECT SUM(total) FROM invoices", conn).iloc[0,0] or 0
    exps = pd.read_sql("SELECT SUM(amount) FROM expenses", conn).iloc[0,0] or 0
    st.metric("Total Sales", f"Rs {sales}")
    st.metric("Total Shop Expenses", f"Rs {exps}")
    st.metric("Net Profit", f"Rs {sales - exps}")
