import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
import requests

# Page configuration
st.set_page_config(page_title="Investment Tracker", layout="wide")

st.title("💰 Investment Tracker")

# --- Session State Management ---
if 'custom_tickers' not in st.session_state:
    st.session_state.custom_tickers = {}

# --- Helper Functions ---
def search_yahoo_finance(query):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=5&newsCount=0"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        data = response.json()
        if 'quotes' in data:
            return data['quotes']
    except Exception as e:
        st.error(f"Search failed: {e}")
    return []

# --- Sidebar Configuration ---
st.sidebar.header("Configuration")

# 1. Date Selection (Updated: End Date is always Today)
st.sidebar.subheader("📅 Investment Period")
start_date_input = st.sidebar.date_input("Start Date", date(2020, 1, 1))
end_date_input = st.sidebar.date_input("End Date", datetime.today()) # 오늘 날짜로 자동 설정

START_DATE = start_date_input.strftime("%Y-%m-%d")
END_DATE = end_date_input.strftime("%Y-%m-%d")

# 2. Investment Amount
MONTHLY_INVESTMENT = st.sidebar.number_input("Monthly Investment ($)", value=100, step=10)

# 3. Ticker Selection
st.sidebar.subheader("📈 Assets")

# Predefined list
PREDEFINED_TICKERS = {
    "S&P 500 (^GSPC)": "^GSPC",
    "Nasdaq (^IXIC)": "^IXIC",
    "SCHD (SCHD)": "SCHD",
    "Apple (AAPL)": "AAPL",
    "Google (GOOGL)": "GOOGL",
    "Microsoft (MSFT)": "MSFT",
    "Amazon (AMZN)": "AMZN",
    "Tesla (TSLA)": "TSLA",
    "Nvidia (NVDA)": "NVDA",
    "Meta (META)": "META",
    "Berkshire Hathaway (BRK-B)": "BRK-B",
    "TSMC (TSM)": "TSM",
    "Samsung Electronics (005930.KS)": "005930.KS",
    "SK Hynix (000660.KS)": "000660.KS",
    "Naver (035420.KS)": "035420.KS",
    "Kakao (035720.KS)": "035720.KS",
    "Hyundai Motor (005380.KS)": "005380.KS",
    "Gold (GC=F)": "GC=F",
    "Bitcoin (BTC-USD)": "BTC-USD",
    "Ethereum (ETH-USD)": "ETH-USD",
    "QQQ (QQQ)": "QQQ",
    "SPY (SPY)": "SPY",
    "TQQQ (TQQQ)": "TQQQ",
    "SOXL (SOXL)": "SOXL",
}

# Multiselect for predefined
selected_names = st.sidebar.multiselect(
    "Select Assets", 
    options=list(PREDEFINED_TICKERS.keys()), 
    default=["S&P 500 (^GSPC)", "Nasdaq (^IXIC)", "SCHD (SCHD)"]
)

# Build dictionary from predefined selection
selected_tickers = {name: PREDEFINED_TICKERS[name] for name in selected_names}

# --- Search & Add Section ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Search & Add")
search_query = st.sidebar.text_input("Search Yahoo Finance", placeholder="e.g. Netflix, 005930")

if search_query:
    results = search_yahoo_finance(search_query)
    if results:
        st.sidebar.markdown("**Results:**")
        for item in results:
            symbol = item.get('symbol')
            shortname = item.get('shortname', symbol)
            exchDisp = item.get('exchDisp', '')
            typeDisp = item.get('typeDisp', '')
            
            label = f"{shortname} ({symbol}) - {exchDisp}"
            
            if st.sidebar.button(f"➕ {label}", key=symbol):
                st.session_state.custom_tickers[f"{shortname} ({symbol})"] = symbol
                st.rerun()
    else:
        st.sidebar.info("No results found.")

# Display and manage custom added tickers
if st.session_state.custom_tickers:
    st.sidebar.markdown("**Added Custom Assets:**")
    for name, symbol in list(st.session_state.custom_tickers.items()):
        col1, col2 = st.sidebar.columns([0.8, 0.2])
        col1.text(name)
        if col2.button("❌", key=f"remove_{symbol}"):
            del st.session_state.custom_tickers[name]
            st.rerun()
        
        # Add to selected tickers
        selected_tickers[name] = symbol

# Deduplicate tickers (keep the first occurrence of each symbol)
unique_tickers = {}
seen_symbols = set()
for name, symbol in selected_tickers.items():
    if symbol not in seen_symbols:
        unique_tickers[name] = symbol
        seen_symbols.add(symbol)
selected_tickers = unique_tickers

# --- Buy Me a Coffee Section ---
st.sidebar.markdown("---")
st.sidebar.markdown("### ☕ Support this app")

# TODO: 본인의 Buy Me a Coffee 아이디로 변경하세요!
buymeacoffee_url = "https://www.buymeacoffee.com/YOUR_USERNAME"

st.sidebar.markdown(f"""
<a href="{buymeacoffee_url}" target="_blank">
<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" >
</a>
""", unsafe_allow_html=True)


# --- Main Logic ---

# 1. Text Description
st.markdown(f"### 🧐 What if you invested **${MONTHLY_INVESTMENT}** every month?")
st.markdown(f"Simulation period: **{START_DATE}** to **{END_DATE}**")

st.info("""
ℹ️ **Simulation Notes**:
- Investments occur on the **first trading day** of each month.
- **Dividends are not included** in this calculation.
""")

@st.cache_data
def load_data(ticker_dict, start, end):
    if not ticker_dict:
        return pd.DataFrame()
        
    symbols = list(ticker_dict.values())
    # Download data
    data = yf.download(symbols, start=start, end=end, auto_adjust=False)['Adj Close']
    
    # Handle single ticker case (returns Series)
    if isinstance(data, pd.Series):
        data = data.to_frame(name=symbols[0])
        
    # Resample to monthly frequency (Month Start) and take the first valid price
    monthly_data = data.resample('MS').first()
    return monthly_data

def calculate_portfolio(data, ticker_symbol, monthly_inv):
    # Handle case where data might be missing the column
    if ticker_symbol not in data.columns:
        return pd.DataFrame()

    prices = data[ticker_symbol].dropna()
    
    shares_owned = 0
    total_invested = 0
    portfolio_values = []
    invested_values = []
    dates = []
    
    for date, price in prices.items():
        # Buy shares
        shares_bought = monthly_inv / price
        shares_owned += shares_bought
        total_invested += monthly_inv
        
        # Current value
        current_value = shares_owned * price
        
        dates.append(date)
        portfolio_values.append(current_value)
        invested_values.append(total_invested)
        
    return pd.DataFrame({
        "Date": dates,
        "Total Invested": invested_values,
        "Portfolio Value": portfolio_values
    }).set_index("Date")

with st.spinner("Fetching market data..."):
    if not selected_tickers:
        st.warning("Please select at least one asset.")
    else:
        try:
            data = load_data(selected_tickers, START_DATE, END_DATE)
            
            if data.empty:
                st.error("No data found for the selected range/tickers.")
            else:
                combined_df = pd.DataFrame()
                
                # Calculate for each ticker
                for name, symbol in selected_tickers.items():
                    df = calculate_portfolio(data, symbol, MONTHLY_INVESTMENT)
                    
                    if df.empty:
                        st.warning(f"Could not calculate data for {name} ({symbol})")
                        continue

                    # Initialize combined_df with the index and Total Invested from the first valid ticker
                    if combined_df.empty:
                        combined_df = pd.DataFrame(index=df.index)
                        combined_df["Total Invested"] = df["Total Invested"]
                    
                    combined_df[name] = df["Portfolio Value"]

                if combined_df.empty:
                     st.error("Could not calculate portfolio values.")
                else:
                    combined_df = combined_df.ffill()
                    
                    # -----------------------------------------------
                    # [MOVED UP] Metrics Section 
                    # -----------------------------------------------
                    st.subheader(f"Final Performance (As of {END_DATE})")
                    
                    final_invested = combined_df["Total Invested"].iloc[-1]
                    
                    # Create columns dynamically
                    # Filter out tickers that failed to load
                    valid_tickers = [name for name in selected_tickers.keys() if name in combined_df.columns]
                    
                    cols = st.columns(len(valid_tickers) + 1)
                    
                    # First column: Total Invested
                    cols[0].metric("Total Invested", f"${final_invested:,.0f}")
                    
                    # Subsequent columns: Tickers
                    for i, name in enumerate(valid_tickers):
                        final_value = combined_df[name].iloc[-1]
                        return_pct = ((final_value / final_invested) - 1) * 100
                        
                        # Color logic for metric
                        cols[i+1].metric(
                            f"{name}", 
                            f"${final_value:,.0f}", 
                            f"{return_pct:+.1f}%"
                        )
                    
                    st.divider() # 구분선 추가

                    # -----------------------------------------------
                    # [MOVED DOWN] Visualization Section
                    # -----------------------------------------------
                    fig = go.Figure()
                    
                    # Plot Total Invested
                    fig.add_trace(go.Scatter(
                        x=combined_df.index, 
                        y=combined_df["Total Invested"], 
                        mode='lines', 
                        name='Total Invested', 
                        line=dict(dash='dash', color='gray', width=2)
                    ))
                    
                    # Plot each ticker
                    for name in selected_tickers.keys():
                        if name in combined_df.columns:
                            fig.add_trace(go.Scatter(
                                x=combined_df.index, 
                                y=combined_df[name], 
                                mode='lines', 
                                name=name,
                            ))
                    
                    fig.update_layout(
                        title="Portfolio Value Over Time",
                        xaxis_title="Date",
                        yaxis_title="Value ($)",
                        hovermode="x unified",
                        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                        template="plotly_white",
                        height=600  # 높이 약간 조정
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)

                    # Data Table
                    with st.expander("View Raw Data"):
                        st.dataframe(combined_df.style.format("${:,.2f}"))
                        
        except Exception as e:
            st.error(f"An error occurred: {e}")
