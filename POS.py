import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64

# ---------- CONFIG ----------
st.set_page_config("WAA POS", layout="wide")
DB = "waa_full_pos.db"

# ---------- DATABASE SETUP ----------
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# Tables setup
c.execute("CREATE TABLE IF NOT EXISTS inventory(item TEXT PRIMARY KEY, qty INTEGER, price INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS invoices(inv_no INTEGER, date TEXT, customer TEXT, total INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS payments(date TEXT, customer TEXT, amount INTEGER, method TEXT, bank_name TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, opening_balance INTEGER)")
conn.commit()

# --- PDF GENERATION FUNCTION ---
def create_pdf(inv_no, customer, date, items_df, total):
    pdf = FPDF(format=(80, 150)) # Thermal Printer Size
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 5, "WAA Mobile Accessories", ln=True, align='C')
    pdf.set_font("Arial", size=8)
    pdf.cell(0, 5, f"Bill #: {inv_no} | Date: {date}", ln=True, align='C')
    pdf.cell(0, 5, f"Customer: {customer}", ln=True, align='C')
    pdf.line(5, 25, 75, 25)
    
    pdf.set_y(30)
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(35, 5, "Item")
    pdf.cell(10, 5, "Qty")
    pdf.cell(25, 5, "Total", ln=True)
    pdf.set_font("Arial", size=8)
    
    for _, row in items_df.iterrows():
        pdf.cell(35, 5, str(row['Item']))
        pdf.cell(10, 5, str(row['Qty']))
        pdf.cell(25, 5, str(row['Total']), ln=True)
    
    pdf.line(5, pdf.get_y() + 2, 75, pdf.get_y() + 2)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 10, f"Grand Total: Rs {total}", ln=True, align='R')
    pdf.set_font("Arial", 'I', 7)
    pdf.cell(0, 5, "Thank you for your business!", ln=True, align='C')
    
    return pdf.output(dest='S')

# ---------- UI TABS ----------
tabs = st.tabs(["🧾 Sale Invoice", "📦 Inventory", "👥 Customers & Khata", "💰 Receiving"])

# ================= 1. SALE INVOICE (With PDF) =================
with tabs[0]:
    st.subheader("New Sale")
    cust_list = ["Walk-in"] + [r[0] for r in c.execute("SELECT name FROM customers").fetchall()]
    
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
        total_bill = df_cart["Total"].sum()
        st.markdown(f"### 🧾 Total: Rs {total_bill}")
        
        if st.button("💾 Save & Generate PDF"):
            inv_no = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000) + 1
            # Save to Database
            c.execute("INSERT INTO invoices VALUES(?,?,?,?)", (inv_no, s_date.strftime("%Y-%m-%d"), final_customer, total_bill))
            for r in st.session_state.cart:
                c.execute("UPDATE inventory SET qty = qty - ? WHERE item = ?", (r['Qty'], r['Item']))
            conn.commit()
            
            # Create PDF
            pdf_bytes = create_pdf(inv_no, final_customer, s_date.strftime("%Y-%m-%d"), df_cart, total_bill)
            
            # Download Button
            st.download_button(label="📥 Download PDF Bill", data=pdf_bytes, file_name=f"Bill_{inv_no}.pdf", mime="application/pdf")
            
            st.session_state.cart = []
            st.success("Bill Saved and PDF Ready!")
