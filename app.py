import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- Google Sheets Setup ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials (place your JSON file path here)
creds = ServiceAccountCredentials.from_json_keyfile_name("/mnt/c/Users/lenovo/Downloads/cred.json", scope)
client = gspread.authorize(creds)

# Google Sheet setup
sheet = client.open("PKP_Tracker").sheet1

# --- Helper Functions ---
def load_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

def add_transaction(date, etf, price, amount):
    units = amount / price
    row = [str(date), etf, float(price), float(amount), float(units), "BUY", 0]
    sheet.append_row(row)

def book_profit(date, etf, ltp, pkp_avg, df):
    total_units = df[df['ETF'] == etf]['Units'].sum()
    total_cost = df[df['ETF'] == etf]['Amount'].sum()
    market_value = total_units * ltp
    profit = market_value - total_cost

    if profit >= 5000:
        units_to_sell = profit / ltp
        row = [str(date), etf, float(ltp), 0, float(units_to_sell), "SELL", float(profit)]
        sheet.append_row(row)
        return profit, units_to_sell
    return 0, 0

def calculate_pkp_avg(df, etf):
    df = df[df['ETF'] == etf]
    buy_df = df[df['Type'] == 'BUY']
    sell_units = df[df['Type'] == 'SELL']['Units'].sum()
    total_units = buy_df['Units'].sum() - sell_units
    total_cost = buy_df['Amount'].sum() - df[df['Type'] == 'SELL']['Profit'].sum()
    return total_cost / total_units if total_units else 0

# --- UI ---
st.title("🌱 Paiso Ka Ped (PKP) - SIP + Profit Tracker")

menu = ["Add SIP Transaction", "Check PKP Profit", "View Ledger"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Add SIP Transaction":
    st.subheader("📥 Add Weekly SIP")
    date = st.date_input("Date", datetime.today())
    etf = st.text_input("ETF Name (e.g. NiftyBEES)")
    price = st.number_input("Price per unit", min_value=0.0, step=0.01)
    amount = st.number_input("Amount Invested (e.g. ₹20000)", min_value=0.0, step=100.0)
    if st.button("Add Transaction"):
        add_transaction(date, etf, price, amount)
        st.success("Transaction added!")

elif choice == "Check PKP Profit":
    st.subheader("💰 Check for Profit Booking")
    etf = st.text_input("ETF Name (e.g. NiftyBEES)")
    ltp = st.number_input("Latest Traded Price (LTP)", min_value=0.0, step=0.01)
    if st.button("Check Profit"):
        df = load_data()
        pkp_avg = calculate_pkp_avg(df, etf)
        profit, units_sold = book_profit(datetime.today(), etf, ltp, pkp_avg, df)
        if profit >= 5000:
            st.success(f"🎉 Profit of ₹{profit:.2f} booked by selling {units_sold:.2f} units")
        else:
            st.info("No booking yet. Profit < ₹5000 or below PKP average.")

elif choice == "View Ledger":
    st.subheader("📊 Investment Ledger")
    df = load_data()
    st.dataframe(df)

    st.write("---")
    etfs = df['ETF'].unique()
    for etf in etfs:
        etf_df = df[df['ETF'] == etf]
        total_units = etf_df[etf_df['Type'] == 'BUY']['Units'].sum() - etf_df[etf_df['Type'] == 'SELL']['Units'].sum()
        invested = etf_df[etf_df['Type'] == 'BUY']['Amount'].sum()
        booked_profit = etf_df[etf_df['Type'] == 'SELL']['Profit'].sum()
        pkp_avg = calculate_pkp_avg(df, etf)

        st.markdown(f"**{etf}**")
        st.write(f"Total Units: {total_units:.2f}")
        st.write(f"PKP Avg: ₹{pkp_avg:.2f}")
        st.write(f"Total Invested: ₹{invested:.2f}")
        st.write(f"Total Booked Profit: ₹{booked_profit:.2f}")
        st.write("---")
