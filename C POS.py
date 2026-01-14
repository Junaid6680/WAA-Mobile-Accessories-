import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# ---------------- CONFIG ----------------
st.set_page_config("WAA POS Ultimate", layout="wide")
DB = "waa_pos_ultimate.db"

ADMIN_USER = "admin"
ADMIN_PASS = "1234"

conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# ---------------- DATABASE ----------------
c.execute("""CREATE TABLE IF NOT EXISTS inventory(
    item TEXT PRIMARY KEY,
    qty INTEGER,
    cost INTEGER
)""")

c.execute("""CREATE TABLE IF NOT EXISTS invoices(
    inv_no INTEGER,
    date TEXT,
    customer TEXT,
    total INTEGER,
    total_cost INTEGER
)""")

c.execute("""CREATE TABLE IF NOT EXISTS invoice_items(
    inv_no INTEGER,
    item TEXT,
    qty INTEGER,
    rate INTEGER,
    total INTEGER,
    cost INTEGER
)""")

c.execute("""CREATE TABLE IF NOT EXISTS payments(
    date TEXT,
    customer TEXT,
    amount INTEGER,
    method TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS customers(
    name TEXT PRIMARY KEY,
    opening_balance INTEGER
)""")

c.execute("""CREATE TABLE IF NOT EXISTS capital(
    date TEXT,
    partner TEXT,
    amount INTEGER,
    type TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS returns(
    date TEXT,
    customer TEXT,
    item TEXT,
    qty INTEGER,
    amount INTEGER
)""")

conn.commit()

# ---------------- LOGIN ----------------
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 WAA POS Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u == ADMIN_USER and p == ADMIN_PASS:
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Wrong Login!")
    st.stop()

# ---------------- PDF ----------------
def generate_bill(inv, cust, date, df, total):
    pdf = FPDF(format=(80,150))
    pdf.add_page()
    pdf.set_font("Arial","B",12)
    pdf.cell(0,8,"WAA Mobile Accessories",ln=True,align="C")
    pdf.set_font("Arial","",8)
    pdf.cell(0,5,f"Bill#: {inv}",ln=True)
    pdf.cell(0,5,f"Date: {date}",ln=True)
    pdf.cell(0,5,f"Customer: {cust}",ln=True)
    pdf.ln(3)

    pdf.set_font("Arial","B",8)
    pdf.cell(35,5,"Item")
    pdf.cell(10,5,"Qty")
    pdf.cell(20,5,"Total",ln=True)

    pdf.set_font("Arial","",8)
    for _,r in df.iterrows():
        pdf.cell(35,5,r["Item"])
        pdf.cell(10,5,str(r["Qty"]))
        pdf.cell(20,5,str(r["Total"]),ln=True)

    pdf.ln(3)
    pdf.set_font("Arial","B",10)
    pdf.cell(0,8,f"TOTAL: Rs {total}",align="R")
    return pdf.output(dest="S")

# ---------------- TABS ----------------
tabs = st.tabs([
    "🧾 Sale",
    "📦 Inventory",
    "👥 Customers Ledger",
    "💰 Cash Book",
    "🔄 Returns",
    "📊 Profit Report"
])

# ---------------- SALE ----------------
with tabs[0]:
    st.subheader("New Sale")

    custs = ["Walk-in"] + [x[0] for x in c.execute("SELECT name FROM customers")]
    cust = st.selectbox("Customer", custs)

    inv_df = pd.read_sql("SELECT * FROM inventory", conn)

    col1,col2,col3 = st.columns(3)
    item = col1.selectbox("Item", inv_df["item"])
    qty = col2.number_input("Qty",1)
    rate = col3.number_input("Sale Rate",0)

    stock = inv_df.loc[inv_df.item==item,"qty"].values[0]
    cost = inv_df.loc[inv_df.item==item,"cost"].values[0]

    if "cart" not in st.session_state:
        st.session_state.cart = []

    if st.button("Add Item"):
        if qty > stock:
            st.error("❌ Stock kam hai!")
        else:
            st.session_state.cart.append({
                "Item":item,"Qty":qty,
                "Rate":rate,
                "Total":qty*rate,
                "Cost":cost
            })
            st.rerun()

    if st.session_state.cart:
        df = pd.DataFrame(st.session_state.cart)
        st.dataframe(df[["Item","Qty","Rate","Total"]])
        total = df["Total"].sum()
        tcost = (df["Cost"]*df["Qty"]).sum()

        if st.button("Save Invoice"):
            inv = (c.execute("SELECT MAX(inv_no) FROM invoices").fetchone()[0] or 1000)+1
            today = datetime.now().strftime("%Y-%m-%d")

            c.execute("INSERT INTO invoices VALUES(?,?,?,?,?)",
                      (inv,today,cust,total,tcost))

            for r in st.session_state.cart:
                c.execute("INSERT INTO invoice_items VALUES(?,?,?,?,?,?)",
                          (inv,r["Item"],r["Qty"],r["Rate"],r["Total"],r["Cost"]))
                c.execute("UPDATE inventory SET qty=qty-? WHERE item=?",
                          (r["Qty"],r["Item"]))

            conn.commit()

            pdf = generate_bill(inv,cust,today,df,total)
            st.download_button("Download Bill",pdf,f"WAA_{inv}.pdf","application/pdf")

            st.session_state.cart=[]
            st.success("Invoice Saved!")

# ---------------- INVENTORY ----------------
with tabs[1]:
    st.dataframe(pd.read_sql("SELECT * FROM inventory",conn),use_container_width=True)

# ---------------- LEDGER ----------------
with tabs[2]:
    led=[]
    for _,r in pd.read_sql("SELECT * FROM customers",conn).iterrows():
        name=r["name"]
        sale=pd.read_sql("SELECT SUM(total) FROM invoices WHERE customer=?",
                          conn,params=(name,)).iloc[0,0] or 0
        paid=pd.read_sql("SELECT SUM(amount) FROM payments WHERE customer=?",
                          conn,params=(name,)).iloc[0,0] or 0
        led.append({
            "Customer":name,
            "Balance":r["opening_balance"]+sale-paid
        })
    st.dataframe(pd.DataFrame(led),use_container_width=True)

# ---------------- CASH BOOK ----------------
with tabs[3]:
    df=pd.read_sql("SELECT method,SUM(amount) amt FROM payments GROUP BY method",conn)
    st.dataframe(df)

# ---------------- RETURNS ----------------
with tabs[4]:
    cust=st.selectbox("Customer",custs)
    item=st.selectbox("Item",inv_df["item"])
    qty=st.number_input("Qty",1)
    amt=st.number_input("Amount",0)
    if st.button("Save Return"):
        c.execute("INSERT INTO returns VALUES(?,?,?,?,?)",
                  (datetime.now().strftime("%Y-%m-%d"),cust,item,qty,amt))
        c.execute("UPDATE inventory SET qty=qty+? WHERE item=?",(qty,item))
        conn.commit()
        st.success("Return Saved")

# ---------------- PROFIT ----------------
with tabs[5]:
    df=pd.read_sql("SELECT SUM(total) sales, SUM(total_cost) cost FROM invoices",conn)
    profit=(df.sales[0] or 0)-(df.cost[0] or 0)
    st.metric("Net Profit",f"Rs {profit}")
