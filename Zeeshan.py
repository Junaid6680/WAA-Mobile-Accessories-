import streamlit as st
import pandas as pd
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Zeeshan Mobile POS", layout="wide")

# Custom CSS for Watermark and Styling
st.markdown("""
    <style>
    .reportview-container {
        background: url("https://www.transparenttextures.com/patterns/cubes.png");
    }
    .watermark {
        position: fixed;
        bottom: 10%;
        left: 25%;
        opacity: 0.1;
        z-index: -1;
        font-size: 100px;
        transform: rotate(-45deg);
    }
    </style>
    <div class="watermark">ZEESHAN MOBILE</div>
    """, unsafe_allow_html=True)

# Header Section
st.title("📱 Zeeshan Mobile Accessories")
st.subheader("Contact: 03296971255")
st.divider()

# Session State for Data Storage (Temporary Database)
if 'inventory' not in st.session_state:
    st.session_state.inventory = []
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=["Date", "Customer", "Contact", "Total", "Paid", "Balance"])

# Layout: Billing & Ledger
tab1, tab2 = st.tabs(["🛒 Create Bill", "📒 Customer Ledger"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        cust_name = st.text_input("Customer Name")
        cust_phone = st.text_input("Customer Phone")
    
    with col2:
        item_name = st.text_input("Item Name (e.g. Data Cable)")
        item_price = st.number_input("Price", min_value=0, step=10)
        if st.button("Add Item"):
            st.session_state.inventory.append({"Item": item_name, "Price": item_price})
            st.success(f"{item_name} added!")

    # Display Current Items
    if st.session_state.inventory:
        df_bill = pd.DataFrame(st.session_state.inventory)
        st.table(df_bill)
        total_amt = df_bill["Price"].sum()
        st.write(f"### Total Amount: Rs. {total_amt}")
        
        paid_amt = st.number_input("Amount Paid", min_value=0)
        balance = total_amt - paid_amt
        
        if st.button("Finalize & Save Bill"):
            new_entry = {
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Customer": cust_name,
                "Contact": cust_phone,
                "Total": total_amt,
                "Paid": paid_amt,
                "Balance": balance
            }
            st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_entry])], ignore_index=True)
            st.session_state.inventory = [] # Reset for next bill
            st.balloons()
            st.success("Bill Saved to Ledger!")

with tab2:
    st.header("Customer Khata / Ledger")
    st.dataframe(st.session_state.ledger, use_container_width=True)
    
    # Simple Search
    search = st.text_input("Search Customer Name")
    if search:
        filtered_df = st.session_state.ledger[st.session_state.ledger['Customer'].str.contains(search, case=False)]
        st.write(filtered_df)
