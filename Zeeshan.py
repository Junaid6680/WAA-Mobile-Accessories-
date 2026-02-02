import streamlit as st
import pandas as pd
from fpdf import FPDF
import os

# --- Page Config ---
st.set_page_config(page_title="Zeeshan Mobile POS", layout="wide")

# --- CSS for Watermark & Style ---
st.markdown("""
    <style>
    .watermark {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-45deg);
        opacity: 0.05;
        font-size: 80px;
        color: gray;
        z-index: -1;
        pointer-events: none;
    }
    </style>
    <div class="watermark">ZEESHAN MOBILE ACCESSORIES</div>
    """, unsafe_allow_html=True)

# --- Data Persistence (Session State) ---
if 'customer_db' not in st.session_state:
    # Format: {"Customer Name": {"phone": "123", "balance": 0.0}}
    st.session_state.customer_db = {"Walking Customer": {"phone": "-", "balance": 0.0}}

if 'temp_items' not in st.session_state:
    st.session_state.temp_items = []

# --- PDF Generation Function ---
def create_pdf(cust_name, phone, items, bill_total, old_bal, paid_amt):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 10, "ZEESHAN MOBILE ACCESSORIES", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(190, 7, "Contact: 03296971255", ln=True, align='C')
    pdf.ln(10)
    
    # Customer Info
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 8, f"Customer: {cust_name}")
    pdf.cell(95, 8, f"Date: {pd.Timestamp.now().strftime('%d-%b-%Y')}", ln=True, align='R')
    pdf.cell(95, 8, f"Phone: {phone}")
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 10, "Item Name", 1, 0, 'C', True)
    pdf.cell(30, 10, "Qty", 1, 0, 'C', True)
    pdf.cell(40, 10, "Unit Price", 1, 0, 'C', True)
    pdf.cell(40, 10, "Total", 1, 1, 'C', True)
    
    # Table Rows
    pdf.set_font("Arial", '', 10)
    for item in items:
        pdf.cell(80, 10, f" {item['Item']}", 1)
        pdf.cell(30, 10, str(item['Qty']), 1, 0, 'C')
        pdf.cell(40, 10, str(item['Price']), 1, 0, 'C')
        pdf.cell(40, 10, str(item['Total']), 1, 1, 'C')
    
    # Summary
    pdf.ln(5)
    new_bal = (bill_total + old_bal) - paid_amt
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(150, 8, "Current Bill:", 0, 0, 'R')
    pdf.cell(40, 8, f"Rs. {bill_total}", 1, 1, 'C')
    pdf.cell(150, 8, "Previous Balance (Udhaar):", 0, 0, 'R')
    pdf.cell(40, 8, f"Rs. {old_bal}", 1, 1, 'C')
    pdf.cell(150, 8, "Total Payable:", 0, 0, 'R')
    pdf.cell(40, 8, f"Rs. {bill_total + old_bal}", 1, 1, 'C')
    pdf.set_fill_color(255, 200, 200)
    pdf.cell(150, 8, "Amount Paid:", 0, 0, 'R')
    pdf.cell(40, 8, f"Rs. {paid_amt}", 1, 1, 'C', True)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(150, 10, "Remaining Balance (Ladger):", 0, 0, 'R')
    pdf.cell(40, 10, f"Rs. {new_bal}", 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- UI Interface ---
st.title("🛒 Zeeshan Mobile Accessories POS")

col_main, col_sidebar = st.columns([2, 1])

with col_sidebar:
    st.header("👤 Customer Management")
    # Add New Customer
    with st.expander("Add New Customer"):
        name_in = st.text_input("Full Name")
        phone_in = st.text_input("Phone Number")
        init_bal = st.number_input("Opening Balance (if any)", min_value=0.0)
        if st.button("Save to Database"):
            if name_in:
                st.session_state.customer_db[name_in] = {"phone": phone_in, "balance": init_bal}
                st.success("Customer Added!")
                st.rerun()

    # Selection
    customer_list = list(st.session_state.customer_db.keys())
    selected_cust = st.selectbox("Select Customer for Billing", customer_list)
    cust_data = st.session_state.customer_db[selected_cust]
    st.info(f"📌 **Current Ledger Balance: Rs. {cust_data['balance']}**")

with col_main:
    st.header("📦 Billing Section")
    
    # Item Entry Row
    c1, c2, c3 = st.columns([3, 1, 1])
    item_name = c1.text_input("Item Description")
    item_qty = c2.number_input("Qty", min_value=1, value=1)
    item_price = c3.number_input("Price", min_value=0, value=0)
    
    if st.button("➕ Add Item to Bill"):
        if item_name:
            st.session_state.temp_items.append({
                "Item": item_name,
                "Qty": item_qty,
                "Price": item_price,
                "Total": item_qty * item_price
            })
    
    # Show Current Bill Table
    if st.session_state.temp_items:
        df = pd.DataFrame(st.session_state.temp_items)
        st.table(df)
        
        current_total = df['Total'].sum()
        st.metric("Total Bill Amount", f"Rs. {current_total}")
        
        # Payment Section
        st.divider()
        paid_today = st.number_input("Amount Paid by Customer", min_value=0.0)
        
        if st.button("✅ Finalize & Save Bill"):
            # Update Customer Ledger
            old_bal = cust_data['balance']
            new_bal = (current_total + old_bal) - paid_today
            st.session_state.customer_db[selected_cust]['balance'] = new_bal
            
            # Generate PDF
            pdf_data = create_pdf(selected_cust, cust_data['phone'], st.session_state.temp_items, current_total, old_bal, paid_today)
            
            st.download_button(
                label="📥 Download & Print Bill (PDF)",
                data=pdf_data,
                file_name=f"Bill_{selected_cust}_{pd.Timestamp.now().strftime('%H%M%S')}.pdf",
                mime="application/pdf"
            )
            
            # Reset Bill
            st.session_state.temp_items = []
            st.success(f"Bill Saved! {selected_cust}'s new balance is Rs. {new_bal}")
            
    else:
        st.warning("Bill is empty. Please add items.")

# --- Footer Ledger View ---
st.divider()
st.header("📒 Full Ledger Overview")
ledger_df = pd.DataFrame.from_dict(st.session_state.customer_db, orient='index').reset_index()
ledger_df.columns = ["Customer Name", "Phone", "Remaining Balance"]
st.dataframe(ledger_df, use_container_width=True)
