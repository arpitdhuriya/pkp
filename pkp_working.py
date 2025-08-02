import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import math
import yfinance as yf

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
    units = math.floor(amount / price)  # Buy whole units only
    adjusted_amount = units * price     # Adjust amount to whole units
    row = [str(date), etf, float(price), float(adjusted_amount), float(units), "BUY", 0]
    sheet.append_row(row)

def calculate_pkp_avg(df, etf):
    df = df[df['ETF'] == etf]
    buy_df = df[df['Type'] == 'BUY']
    sell_units = df[df['Type'] == 'SELL']['Units'].sum()
    total_units = buy_df['Units'].sum() - sell_units
    total_cost = buy_df['Amount'].sum()
    return total_cost / total_units if total_units else 0

def book_profit(date, etf, ltp, pkp_avg, df):
    buy_df = df[df['Type'] == 'BUY']
    sell_units = df[df['Type'] == 'SELL']['Units'].sum()
    total_units = buy_df['Units'].sum() - sell_units
    total_cost = df[df['ETF'] == etf]['Amount'].sum()
    market_value = total_units * ltp
    profit = market_value - total_cost
    st.write(f"profit: {profit}, total_cost: {total_cost}, market_value: {market_value}")
    if profit >= 5000:
        units_to_sell = math.floor(profit / ltp)  # Ensure whole unit selling
        est_profit = units_to_sell * ltp 

        confirm = st.radio("💬 Do you want to book this profit?", ("No", "Yes"), key="confirm_profit")
        if confirm == "Yes":
            editable_profit = st.number_input("Edit Profit Amount (Optional)", value=float(est_profit), step=100.0)
            row = [str(date), etf, float(ltp), 0, float(units_to_sell), "SELL", float(editable_profit)]
            sheet.append_row(row)
            return editable_profit, units_to_sell
        else:
            st.info(f"Profit booking cancelled. Estimated profit: ₹{est_profit:.2f} units to sell {units_to_sell}.")
            st.write("No changes made to the ledger.")
            return 0, 0
    return 0, 0

# --- UI ---
st.title("🌱 Paiso Ka Ped (PKP) - SIP + Profit Tracker")

menu = ["Add SIP Transaction", "Check PKP Profit", "View Ledger"]
choice = st.sidebar.selectbox("Menu", menu)

df = load_data()

if choice == "Add SIP Transaction":
    st.subheader("📥 Add Weekly SIP")
    date = st.date_input("Date", datetime.today())
    etf = st.text_input("ETF Name (e.g. NiftyBEES)")
    price = st.number_input("Price per unit", min_value=0.0, step=0.01)
    amount = st.number_input("Amount Invested (e.g. ₹20000)", min_value=0.0, step=100.0)
    
    if price > 0 and amount > 0:
        units = math.floor(amount / price)
        adjusted_amount = units * price
        st.info(f"🧮 Will purchase {units} units for ₹{adjusted_amount:.2f} (rounded to whole units).")
    
    if st.button("Add Transaction"):
        add_transaction(date, etf, price, amount)
        st.success("Transaction added!")

elif choice == "Check PKP Profit":
    st.subheader("💰 Check for Profit Booking")
    etf = st.text_input("ETF Name (e.g. NiftyBEES)")
    ltp = st.number_input("Latest Traded Price (LTP)", min_value=0.0, step=0.01)
    if etf:
        ticker_map = {
            "NiftyBEES": "NIFTYBEES.NS",  # BSE ticker
            "BankBEES": "BANKBEES.NS"
            }
        ticker_symbol = ticker_map.get(etf.strip(), None)

        if ticker_symbol:
            try:
                ticker = yf.Ticker(ticker_symbol)
                ltp = ticker.history(period='1d')['Close'].iloc[-1]
                st.success(f"✅ Latest LTP for {etf} fetched from Yahoo Finance: ₹{ltp:.2f}")
            except:
                st.warning("⚠️ Could not fetch live data. Please enter LTP manually.")
        else:
            ltp = st.number_input("Enter LTP manually (ETF not in ticker map)", min_value=0.0, step=0.01)
    else:
        ltp = st.number_input("Enter ETF and then fetch LTP", min_value=0.0, step=0.01)
    if etf and ltp > 0:
        pkp_avg = calculate_pkp_avg(df, etf)
        st.write(f"📉 Current PKP Average: ₹{pkp_avg:.2f}")
        profit, units_sold = book_profit(datetime.today(), etf, ltp, pkp_avg, df)
        if profit >= 5000:
            st.success(f"🎉 Profit of ₹{profit:.2f} booked by selling {units_sold:.2f} units")
        elif profit == 0:
            st.info("No profit booking performed or cancelled.")
        else:
            st.info("Profit < ₹5000 or below PKP average.")

elif choice == "View Ledger":
    st.subheader("📊 Investment Ledger")
    st.dataframe(df)

st.write("---")
if not df.empty:
    etfs = df['ETF'].unique()
    for etf in etfs:
        etf_df = df[df['ETF'] == etf]
        total_units = etf_df[etf_df['Type'] == 'BUY']['Units'].sum() - etf_df[etf_df['Type'] == 'SELL']['Units'].sum()
        invested = etf_df[etf_df['Type'] == 'BUY']['Amount'].sum()
        booked_profit = etf_df[etf_df['Type'] == 'SELL']['Profit'].sum()
        pkp_avg = calculate_pkp_avg(df, etf)

        st.markdown(f"### 📌 {etf} Summary")
        st.write(f"- **Total Units**: {total_units:.0f}")
        st.write(f"- **PKP Avg**: ₹{pkp_avg:.2f}")
        st.write(f"- **Total Invested**: ₹{invested:.2f}")
        st.write(f"- **Total Booked Profit**: ₹{booked_profit:.2f}")
        st.write("---")
