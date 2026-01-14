import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import re

# ---------- CONFIG ----------
st.set_page_config("WAA POS Ultimate", layout="wide")
DB = "waa_mobile_v5_final.db"

# Initialize database connection with users table
@st.cache_resource
def init_db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    c = conn.cursor()
    
    # ---------- USER AUTHENTICATION TABLES ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            role TEXT,
            created_at TEXT,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    # Create default admin user if not exists
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        # Default password: admin123 (will be hashed)
        hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("""
            INSERT INTO users (username, password, full_name, role, created_at)
            VALUES(?,?,?,?,?)
        """, ("admin", hashed_pw, "Administrator", "admin", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    # ---------- DATABASE TABLES ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory(
            item TEXT PRIMARY KEY, 
            qty INTEGER, 
            cost INTEGER,
            category TEXT,
            min_stock INTEGER DEFAULT 10
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS invoices(
            inv_no INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, 
            customer TEXT, 
            total INTEGER, 
            total_cost INTEGER,
            payment_method TEXT DEFAULT 'Cash',
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inv_no INTEGER,
            item TEXT,
            qty INTEGER,
            rate INTEGER,
            total INTEGER,
            FOREIGN KEY(inv_no) REFERENCES invoices(inv_no)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, 
            customer TEXT, 
            amount INTEGER, 
            method TEXT,
            reference TEXT,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers(
            name TEXT PRIMARY KEY, 
            opening_balance INTEGER,
            phone TEXT,
            email TEXT,
            address TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS capital(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, 
            partner TEXT, 
            amount INTEGER, 
            type TEXT,
            description TEXT,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS returns(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, 
            customer TEXT, 
            item TEXT, 
            qty INTEGER, 
            amount INTEGER,
            reason TEXT,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            description TEXT,
            amount INTEGER,
            payment_method TEXT,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    
    # --- 15 ITEMS WITH COST ---
    sample_items = [
        ("iPhone 13 Case", 50, 400, "Cases & Covers"),
        ("iPhone 14 Glass", 100, 150, "Screen Protectors"),
        ("Samsung 25W Adapter", 30, 1200, "Chargers"),
        ("Type-C Cable", 40, 300, "Cables"),
        ("Airpods Pro 2", 15, 2500, "Audio"),
        ("M10 TWS Earbuds", 25, 650, "Audio"),
        ("65W Fast Charger", 20, 1800, "Chargers"),
        ("Micro USB Cable", 60, 120, "Cables"),
        ("Phone Tripod", 10, 500, "Accessories"),
        ("Power Bank 20k", 12, 3500, "Power Banks"),
        ("Mini Speaker", 18, 900, "Audio"),
        ("Gaming Headset", 8, 2200, "Audio"),
        ("Smart Watch Ultra", 15, 2800, "Wearables"),
        ("Car Mount", 35, 250, "Accessories"),
        ("OTG Adapter", 80, 80, "Adapters")
    ]
    for name, q, cost, category in sample_items:
        c.execute("INSERT OR IGNORE INTO inventory (item, qty, cost, category) VALUES(?,?,?,?)", 
                 (name, q, cost, category))
    
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# ---------- AUTHENTICATION FUNCTIONS ----------
def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    """Authenticate user credentials"""
    hashed_pw = hash_password(password)
    c.execute("SELECT id, username, full_name, role FROM users WHERE username = ? AND password = ? AND is_active = 1", 
              (username, hashed_pw))
    return c.fetchone()

def register_user(username, password, full_name, role):
    """Register new user"""
    try:
        # Check if username exists
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            return False, "Username already exists"
        
        # Validate password strength
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        hashed_pw = hash_password(password)
        c.execute
