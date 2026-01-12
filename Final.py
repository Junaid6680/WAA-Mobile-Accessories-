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

# ---------- DATABASE ----------
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
    customer = st.text_input("Customer Name")
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    
    col1, col2, col3 = st.columns(3)
    with col1: item = st.selectbox("Item Select", inv_df["item"]) if not inv_df.empty else None
    with col2: qty = st.number_input("Qty", 1, min_value=1)
    with col3: 
        if item:
            price = inv_df.loc[inv_df.item==item, "price"].values[0]
            st.write(f"Price: {price}")

    if st.button("➕ Add to Cart"):
        stock = inv_df.loc[inv_df.item==item, "qty"].values[0]
        if qty > stock: st.error("Stock nahi hai!")
        else: st.session_state.cart_sale.append({"item": item, "qty": qty, "price": price, "total": qty*price})

    if st.session_state.cart_sale:
        df_cart = pd.DataFrame(st.session_state.cart_sale)
        st.table(df_cart)
        grand_total = df_cart["total"].sum()
        st.metric("Total Bill", f"Rs {grand_total}")
        
        if st.button("💾 Save Invoice"):
            last_inv = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000
            new_no = last_inv + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (new_no, datetime.now().strftime("%Y-%m-%d"), customer, grand_total))
            for r in st.session_state.cart_sale:
                c.execute("INSERT INTO invoice_items VALUES(?,?,?,?,?)", (new_no, r['item'], r['qty'], r['price'], r['total']))
                c.execute("UPDATE inventory SET qty=qty-? WHERE item=?", (r['qty'], r['item']))
            conn.commit()
            st.session_state.cart_sale = []
            st.success("Invoice Saved!")
            st.rerun()

# ================= 2. INVENTORY =================
with tabs[1]:
    st.subheader("Stock Management")
    with st.form("inv_form"):
        n = st.text_input("Item Name")
        q = st.number_input("Stock Qty", 0)
        p = st.number_input("Sale Price", 0)
        if st.form_submit_button("Update Item"):
            c.execute("INSERT OR REPLACE INTO inventory VALUES(?,?,?)",(n,q,p))
            conn.commit()
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

# ================= 3. PURCHASE =================
with tabs[2]:
    st.subheader("Add Purchase (Maal Inward)")
    p_sup = st.text_input("Supplier Name")
    p_item = st.text_input("Item Name")
    p_qty = st.number_input("Qty Received", 1)
    p_cost = st.number_input("Cost Price", 0)
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
    st.subheader("Customer/Supplier Running Khata")
    all_p = pd.read_sql("SELECT DISTINCT customer as name from invoices UNION SELECT DISTINCT supplier from purchases", conn)
    
    if not all_p.empty:
        party = st.selectbox("Select Party", all_p['name'])
        
        # Calculate Balance
        s_total = pd.read_sql("SELECT SUM(total) FROM invoices WHERE customer=?", conn, params=(party,)).iloc[0,0] or 0
        p_total = pd.read_sql("SELECT SUM(total) FROM purchases WHERE supplier=?", conn, params=(party,)).iloc[0,0] or 0
        pay_in = pd.read_sql("SELECT SUM(amount) FROM payments WHERE party=? AND type='In'", conn, params=(party,)).iloc[0,0] or 0
        pay_out = pd.read_sql("SELECT SUM(amount) FROM payments WHERE party=? AND type='Out'", conn, params=(party,)).iloc[0,0] or 0
        
        balance = (s_total - pay_in) - (p_total - pay_out)
        st.metric("Net Balance", f"Rs {balance}", help="Positive: Lena hai, Negative: Dena hai")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            amt = st.number_input("Payment Amount", 0)
            p_type = st.radio("Type", ["In (Paisa Aaya)", "Out (Paisa Diya)"])
        with col_p2:
            meth = st.selectbox("Method", ["Cash", "Bank", "EasyPaisa"])
            if st.button("Record Payment"):
                final_type = "In" if "In" in p_type else "Out"
                c.execute("INSERT INTO payments VALUES(?,?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), party, final_type, meth, amt))
                conn.commit()
                st.rerun()
        
        st.write("Recent Transactions")
        st.dataframe(pd.read_sql("SELECT * FROM payments WHERE party=? ORDER BY date DESC", conn, params=(party,)), use_container_width=True)

# ================= 5. DAILY EXPENSES =================
with tabs[4]:
    st.subheader("Shop Daily Expenses")
    with st.form("exp_form"):
        e_title = st.text_input("Expense Detail (e.g. Bijli Bill, Chai, Rent)")
        e_amt = st.number_input("Amount", 0)
        if st.form_submit_button("Add Expense"):
            c.execute("INSERT INTO expenses VALUES(?,?,?)", (datetime.now().strftime("%Y-%m-%d"), e_title, e_amt))
            conn.commit()
            st.success("Expense Added")
    
    st.write("Today's Expenses")
    today = datetime.now().strftime("%Y-%m-%d")
    st.dataframe(pd.read_sql("SELECT * FROM expenses WHERE date=?", conn, params=(today,)), use_container_width=True)

# ================= 6. REPORTS =================
with tabs[5]:
    st.subheader("Quick Business Overview")
    t_sales = pd.read_sql("SELECT SUM(total) FROM invoices", conn).iloc[0,0] or 0
    t_exp = pd.read_sql("SELECT SUM(amount) FROM expenses", conn).iloc[0,0] or 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sales", f"Rs {t_sales}")
    c2.metric("Total Expenses", f"Rs {t_exp}")
    c3.metric("Gross Profit", f"Rs {t_sales - t_exp}")

    if st.button("Delete Last Invoice (Error Fix)"):
        last_id = c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0]
        if last_id:
            # Revert Stock
            items = c.execute("SELECT item, qty FROM invoice_items WHERE inv_no=?", (last_id,)).fetchall()
            for i, q in items: c.execute("UPDATE inventory SET qty=qty+? WHERE item=?", (q, i))
            c.execute("DELETE FROM invoices WHERE inv_no=?", (last_id,))
            c.execute("DELETE FROM invoice_items WHERE inv_no=?", (last_id,))
            conn.commit()
            st.warning(f"Invoice {last_id} Deleted!")
            st.rerun()
