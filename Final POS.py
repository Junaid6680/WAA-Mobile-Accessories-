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
SHOP_CONTACT = "M Waqas 03154899075 | Farid Khan 03284080860"

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
c.execute("CREATE TABLE IF NOT EXISTS purchase_items(pur_no INTEGER, item TEXT, qty INTEGER, price INTEGER, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, party TEXT, type TEXT, method TEXT, amount INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS expenses(date TEXT, title TEXT, amount INTEGER)")
conn.commit()

# ---------- AUTO-IMPORT STOCK (ONLY ONCE) ----------
def auto_import_stock():
    check = c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    if check == 0:
        initial_stock = [
            ('USB Type-C Cable', 3000, 250),
            ('Micro-USB Cable', 2500, 200),
            ('Lightning Cable (iPhone)', 1500, 400),
            ('Wall Charger (5W)', 700, 500),
            ('Wall Charger (Fast Charging)', 500, 700),
            ('Car Charger', 660, 600),
            ('Power Bank 10000mAh', 300, 1500),
            ('Power Bank 20000mAh', 250, 3000),
            ('Silicone Case (Universal)', 2000, 150),
            ('Hard Case (Brand specific)', 1000, 250),
            ('Flip / Wallet Case', 500, 400),
            ('Tempered Glass (Universal)', 1800, 150),
            ('Full Body Screen Protector', 500, 300),
            ('Wired Earphones', 1500, 250),
            ('Bluetooth Earbuds', 700, 1200),
            ('Over-ear Headphones', 300, 2500),
            ('Bluetooth Speaker (Mini)', 250, 1800),
            ('Smart Watch', 150, 4000),
            ('Fitness Tracker', 300, 2200),
            ('Selfie Stick', 400, 500),
            ('Tripod Stand', 200, 900),
            ('Car Phone Holder', 500, 400),
            ('Pop Socket / Phone Grip', 800, 250),
            ('Rechargeable Battery', 100, 500),
            ('Mobile Repair Toolkit', 50, 1800),
            ('Replacement LCD / Screen', 40, 3500),
            ('OTG Adapter', 1000, 200),
            ('Stylus Pen', 300, 300),
            ('Cleaning Kit', 250, 200)
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

# ---------- SESSION CARTS ----------
if "cart_sale" not in st.session_state: st.session_state.cart_sale = []

# ---------- HEADER ----------
st.markdown(f"<h2 style='text-align:center'>{SHOP_NAME}</h2><p style='text-align:center'>{SHOP_ADDRESS}<br>📞 {SHOP_CONTACT}</p><hr>", unsafe_allow_html=True)

tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "🏭 Purchase", "📝 Khata (Ledger)", "💸 Daily Expenses", "📊 Reports"])

# ================= 1. SALE INVOICE =================
with tabs[0]:
    st.subheader("New Sale")
    customer = st.text_input("Customer Name", value="Walk-in")
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    
    col1, col2, col3 = st.columns(3)
    with col1: 
        item = st.selectbox("Item Select", inv_df["item"]) if not inv_df.empty else None
    with col2: 
        qty = st.number_input("Qty", min_value=1, value=1)
    with col3: 
        if item:
            price = inv_df.loc[inv_df.item==item, "price"].values[0]
            st.write(f"Price: Rs {price}")

    if st.button("➕ Add to Cart"):
        if item:
            stock = inv_df.loc[inv_df.item==item, "qty"].values[0]
            if qty > stock: st.error(f"Stock sirf {stock} bacha hai!")
            else: st.session_state.cart_sale.append({"item": item, "qty": qty, "price": price, "total": qty*price})
        else: st.error("Pehle inventory check karein!")

    if st.session_state.cart_sale:
        df_cart = pd.DataFrame(st.session_state.cart_sale)
        st.table(df_cart)
        grand_total = df_cart["total"].sum()
        st.metric("Total Bill", f"Rs {grand_total}")
        
        if st.button("💾 Save & Print Bill"):
            last_inv = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000
            new_no = last_inv + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (new_no, datetime.now().strftime("%Y-%m-%d"), customer, grand_total))
            for r in st.session_state.cart_sale:
                c.execute("INSERT INTO invoice_items VALUES(?,?,?,?,?)", (new_no, r['item'], r['qty'], r['price'], r['total']))
                c.execute("UPDATE inventory SET qty=qty-? WHERE item=?", (r['qty'], r['item']))
            conn.commit()
            
            # PDF Bill
            pdf = FPDF()
            pdf.add_page()
            if os.path.exists("logo.png"): pdf.image("logo.png", 10, 8, 30)
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
            pdf.ln(2)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"Total Amount: Rs {grand_total}", ln=True, align="R")
            
            os.makedirs("bills", exist_ok=True)
            file_path = f"bills/Bill_{new_no}.pdf"
            pdf.output(file_path)
            
            st.session_state.cart_sale = []
            st.success("Invoice Saved!")
            with open(file_path, "rb") as f:
                st.download_button("⬇️ Download Bill", f, file_name=f"Bill_{new_no}.pdf")

# ================= 2. INVENTORY =================
with tabs[1]:
    st.subheader("Current Stock")
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# ================= 3. PURCHASE =================
with tabs[2]:
    st.subheader("Add Purchase (Maal Inward)")
    p_sup = st.text_input("Supplier Name")
    p_item = st.text_input("Item Name")
    p_qty = st.number_input("Qty Received", min_value=1, value=1)
    p_cost = st.number_input("Cost Price", min_value=0, value=0)
    if st.button("Save Purchase"):
        last_pur = c.execute("SELECT MAX(pur_no) FROM purchases").fetchone()[0] or 5000
        new_p_no = last_pur + 1
        total_p = p_qty * p_cost
        c.execute("INSERT INTO purchases VALUES(?,?,?,?)", (new_p_no, datetime.now().strftime("%Y-%m-%d"), p_sup, total_p))
        c.execute("INSERT INTO purchase_items VALUES(?,?,?,?,?)", (new_p_no, p_item, p_qty, p_cost, total_p))
        c.execute("INSERT OR IGNORE INTO inventory VALUES(?,?,?)", (p_item, 0, p_cost))
        c.execute("UPDATE inventory SET qty=qty+? WHERE item=?", (p_qty, p_item))
        conn.commit()
        st.success("Stock Updated!")

# ================= 4. KHATA (RUNNING LEDGER) =================
with tabs[3]:
    st.subheader("Party Ledger")
    all_p = pd.read_sql("SELECT DISTINCT customer as name from invoices UNION SELECT DISTINCT supplier from purchases", conn)
    if not all_p.empty:
        party = st.selectbox("Select Party", all_p['name'])
        s_total = pd.read_sql("SELECT SUM(total) FROM invoices WHERE customer=?", conn, params=(party,)).iloc[0,0] or 0
        p_total = pd.read_sql("SELECT SUM(total) FROM purchases WHERE supplier=?", conn, params=(party,)).iloc[0,0] or 0
        pay_in = pd.read_sql("SELECT SUM(amount) FROM payments WHERE party=? AND type='In'", conn, params=(party,)).iloc[0,0] or 0
        pay_out = pd.read_sql("SELECT SUM(amount) FROM payments WHERE party=? AND type='Out'", conn, params=(party,)).iloc[0,0] or 0
        balance = (s_total - pay_in) - (p_total - pay_out)
        
        st.metric("Khata Balance", f"Rs {balance}", help="Positive: Aapne lena hai | Negative: Aapne dena hai")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            amt = st.number_input("Payment Amount", min_value=0, value=0)
            p_type = st.radio("Type", ["Received (Customer se aaya)", "Paid (Supplier ko diya)"])
        with col_p2:
            meth = st.selectbox("Method", ["Cash", "Bank", "EasyPaisa"])
            if st.button("Save Payment"):
                final_type = "In" if "Received" in p_type else "Out"
                c.execute("INSERT INTO payments VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), party, final_type, meth, amt))
                conn.commit()
                st.success("Payment Recorded!")
                st.rerun()

# ================= 5. DAILY EXPENSES =================
with tabs[4]:
    st.subheader("Shop Expenses")
    e_title = st.text_input("Expense (Chai, Bill, etc.)")
    e_amt = st.number_input("Amount Paid", min_value=0, value=0)
    if st.button("Record Expense"):
        c.execute("INSERT INTO expenses VALUES(?,?,?)", (datetime.now().strftime("%Y-%m-%d"), e_title, e_amt))
        conn.commit()
        st.success("Expense Saved!")
    st.dataframe(pd.read_sql("SELECT * FROM expenses ORDER BY date DESC", conn), use_container_width=True)

# ================= 6. REPORTS =================
with tabs[5]:
    st.subheader("Business Status")
    t_sales = pd.read_sql("SELECT SUM(total) FROM invoices", conn).iloc[0,0] or 0
    t_exp = pd.read_sql("SELECT SUM(amount) FROM expenses", conn).iloc[0,0] or 0
    
    st.columns(3)[0].metric("Total Sales", f"Rs {t_sales}")
    st.columns(3)[1].metric("Total Expenses", f"Rs {t_exp}")
    st.columns(3)[2].metric("Net Balance", f"Rs {t_sales - t_exp}")
