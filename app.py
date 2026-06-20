import streamlit as st
import pandas as pd
import requests
import time

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="Crypto Trading System (Production Stable)",
    layout="wide"
)

# =========================
# SAFE COINGECKO FETCH (RATE LIMIT PROTECTED)
# =========================

@st.cache_data(ttl=3600)
def fetch_top_200_coingecko():
    url = "https://api.coingecko.com/api/v3/coins/markets"

    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d,30d"
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)

        # Rate limit protection
        if r.status_code == 429:
            st.warning("CoinGecko rate limited (429). Using cached data.")
            return None

        if r.status_code != 200:
            st.error(f"API Error: {r.status_code}")
            return None

        data = r.json()

        if not isinstance(data, list):
            st.error("Unexpected API response format")
            return None

        return data

    except Exception as e:
        st.error(f"Network error: {e}")
        return None

# =========================
# SESSION MEMORY LAYER
# =========================

def get_data():
    if "cached_data" not in st.session_state:
        data = fetch_top_200_coingecko()

        if data:
            st.session_state.cached_data = data
            st.session_state.last_update = time.time()

    return st.session_state.get("cached_data", [])

# =========================
# REFRESH CONTROL
# =========================

def should_refresh(interval=1800):  # 30 min default
    now = time.time()

    if "last_update" not in st.session_state:
        return True

    return (now - st.session_state.last_update) > interval

# =========================
# DATA BUILDER
# =========================

def build_dataframe(data):
    coins = []

    for c in data:
        coins.append({
            "name": c.get("name"),
            "symbol": c.get("symbol", "").upper(),
            "price": c.get("current_price"),
            "market_cap": c.get("market_cap"),
            "volume": c.get("total_volume"),
            "change_24h": c.get("price_change_percentage_24h"),
            "change_7d": c.get("price_change_percentage_7d_in_currency"),
            "change_30d": c.get("price_change_percentage_30d_in_currency"),
            "high_24h": c.get("high_24h"),
            "low_24h": c.get("low_24h")
        })

    return pd.DataFrame(coins)

# =========================
# MAIN APP
# =========================

st.title("🚀 Crypto Trading System (Production Stable)")

# =========================
# AUTO REFRESH CONTROL
# =========================

auto = st.sidebar.checkbox("Auto Refresh (Safe Mode)")

if auto:
    st.sidebar.info("Refreshing every 30 minutes (rate-limit safe)")
    time.sleep(1800)
    st.rerun()

# =========================
# CONTROLLED DATA LOADING
# =========================

if should_refresh():
    data = fetch_top_200_coingecko()

    if data:
        st.session_state.cached_data = data
        st.session_state.last_update = time.time()

df = build_dataframe(get_data())

if df.empty:
    st.warning("No data available (API rate limit or cache empty)")
    st.stop()

# =========================
# METRICS DASHBOARD
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Coins Loaded", len(df))

with col2:
    st.metric("Top Market Cap", f"${df['market_cap'].max():,.0f}")

with col3:
    st.metric("Avg 24h Change", round(df["change_24h"].mean(), 2))

st.divider()

# =========================
# FILTERS
# =========================

st.sidebar.title("Filters")

min_volume = st.sidebar.slider("Min Volume", 0, 1_000_000_000, 10_000_000)
min_market_cap = st.sidebar.slider("Min Market Cap (B)", 0, 200, 1)

df = df[df["volume"] >= min_volume]
df = df[df["market_cap"] >= min_market_cap * 1e9]

# =========================
# DISPLAY TABLE
# =========================

st.subheader("📊 Top 200 Market Overview")

st.dataframe(df, use_container_width=True)

# =========================
# TOP MOVERS
# =========================

st.subheader("🔥 Top Movers (24h)")

top = df.sort_values("change_24h", ascending=False).head(10)

for _, row in top.iterrows():
    st.success(f"""
{row['name']} ({row['symbol']})

💰 Price: ${row['price']}
📈 24h: {row['change_24h']:.2f}%
📊 Market Cap: ${row['market_cap']:,.0f}
💧 Volume: ${row['volume']:,.0f}
""")

# =========================
# STATUS
# =========================

st.sidebar.caption("API Status: CoinGecko (cached + rate-safe)")
