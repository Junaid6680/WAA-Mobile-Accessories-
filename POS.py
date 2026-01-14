import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64

# ---------- CONFIG ----------
st.set_page_config("WAA POS", layout="wide")
DB = "waa_full_pos.db"

# Shop Information
SHOP_NAME = "WAA Mobile Accessories"
SHOP_DETAILS = "Shop No T27, 3rd Floor, Hassan Center 2, Hall Road Lahore\nContact: 03154899075 | 03284080860"

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Tables Create/Ensure
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS capital(date TEXT, partner TEXT, amount INTEGER, type TEXT)")
conn.commit()

# --- PDF GENERATION FUNCTION ---
def create_pdf(inv_no, customer, date, items_df, total):
    pdf = FPDF(format=(80, 150)) # 80mm Thermal Paper
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 5, SHOP_NAME, ln=True, align='C')
    pdf.set_font("Arial", size=7)
    pdf.multi_cell(0, 4, SHOP_DETAILS, align='C')
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(0, 5, f"Invoice: {inv_no} | Date: {date}", ln=True, align='C')
    pdf.cell(0, 5, f"Customer: {customer}", ln=True, align='C')
    pdf.line(5, pdf.get_y(), 75, pdf.get_y())
    
    pdf.ln(2)
    pdf.cell(35, 5, "Item")
    pdf.cell(10, 5, "Qty")
    pdf.cell(25, 5, "Total", ln=True)
    pdf.set_font("Arial", size=8)
    
    for _, row in items_df.iterrows():
        pdf.cell(35, 5, str(row['Item']))
        pdf.cell(10, 5, str(row['Qty']))
        pdf.cell(25, 5, str(row['Total']), ln=True)
    
    pdf.line(5, pdf.get_y() + 2, 75, pdf.get_y() + 2)
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, f"Grand Total: Rs {total}", ln=True, align='R')
    pdf.set_font("Arial", 'I', 7)
    pdf.cell(0, 5, "Software by Gemini AI", ln=True, align='C')
    return pdf.output(dest='S')

# ---------- UI TABS ----------
st.title(f"🏢 {SHOP_NAME}")
tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory Management", "👥 Customers & Khata", "💰 Receiving", "🤝 Capital Account"])

# ================= 1. SALE INVOICE (Fixed Calculation & PDF) =================
with tabs[0]:
    st.subheader("New Sale")
    cust_data = pd.read_sql("SELECT name FROM customers", conn)
    cust_list = ["Walk-in"] + cust_data['name'].tolist()
    
    col1, col2 = st.columns(2)
    with col1: 
        selected_cust = st.selectbox("Select Customer", cust_list)
        final_customer = st.text_input("Customer Name", value="Walk-in Customer") if selected_cust == "Walk-in" else selected_cust
    with col2: s_date = st.date_input("Date", datetime.now())

    inv_data = pd.read_sql("SELECT * FROM inventory", conn)
    c1, c2 = st.columns(2)
    with c1: itm = st.selectbox("Select Item", inv_data["item"]) if not inv_data.empty else None
    with c2: q = st.number_input("Quantity", min_value=1, value=1)
    
    if "cart" not in st.session_state: st.session_state.cart = []
    
    if st.button("➕ Add to Bill"):
        if itm:
            price = inv_data.loc[inv_data.item == itm, "price"].values[0]
            st.session_state.cart.append({"Item": itm, "Qty": q, "Price": price, "Total": q*price})
            st.rerun()

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart)
        total_bill = df_cart["Total"].sum()
        st.write(f"### 🧾 Total Bill: Rs {total_bill}")
        
        if st.button("💾 Finalize & Print"):
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (inv_no, s_date.strftime("%Y-%m-%d"), final_customer, total_bill))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            
            pdf_bytes = create_pdf(inv_no, final_customer, s_date.strftime("%Y-%m-%d"), df_cart, total_bill)
            st.download_button("📥 Download/Print PDF Bill", data=pdf_bytes, file_name=f"WAA_Bill_{inv_no}.pdf", mime="application/pdf")
            
            st.session_state.cart = []
            st.success("Sale Recorded!")

# ================= 2. CUSTOMERS & KHATA (Fixed Ledger) =================
with tabs[2]:
    st.subheader("📜 Running Ledger (Udhaar Hisab)")
    all_c = pd.read_sql("SELECT * FROM customers", conn)
    ledger_data = []
    for _, row in all_c.iterrows():
        name = row['name']
        op_bal = row['opening_balance']
        sales = pd.read_sql(f"SELECT SUM(total) FROM invoices WHERE customer='{name}'", conn).iloc[0,0] or 0
        paid = pd.read_sql(f"SELECT SUM(amount) FROM payments WHERE customer='{name}'", conn).iloc[0,0] or 0
        balance = op_bal + sales - paid
        ledger_data.append({"Customer": name, "Old Bal": op_bal, "New Sales": sales, "Total Paid": paid, "Payable": balance})
    
    st.dataframe(pd.DataFrame(ledger_data), use_container_width=True)

# ================= 3. RECEIVING (Fixed) =================
with tabs[3]:
    st.subheader("📥 Receive Payment")
    all_names = list(set([r[0] for r in c.execute("SELECT name FROM customers").fetchall()] + [r[0] for r in c.execute("SELECT customer FROM invoices").fetchall()]))
    r_cust = st.selectbox("From Customer", all_names)
    r_amt = st.number_input("Amount Received", min_value=0)
    r_meth = st.selectbox("Method", ["Cash", "Meezan Bank", "Faysal Bank", "EasyPaisa"])
    if st.button("Save Payment"):
        c.execute("INSERT INTO payments VALUES(?,?,?,?)", (datetime.now().strftime("%Y-%m-%d"), r_cust, r_amt, r_meth))
        conn.commit()
        st.success("Payment Added to Ledger!")
