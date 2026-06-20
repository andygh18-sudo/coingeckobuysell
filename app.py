import streamlit as st
import pandas as pd
import requests
import numpy as np
import time
import random

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="Crypto Trading System Pro",
    layout="wide"
)

# =========================
# SAFE COINGECKO FETCH (429 PROTECTED)
# =========================

@st.cache_data(ttl=1800)
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

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    # =========================
    # RETRY LOGIC (ANTI 429)
    # =========================
    for attempt in range(5):

        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)

            # Rate limit handling
            if r.status_code == 429:
                wait = (2 ** attempt) + random.random()
                time.sleep(wait)
                continue

            if r.status_code != 200:
                return None

            data = r.json()

            if isinstance(data, dict):
                return None

            return data

        except Exception:
            wait = (2 ** attempt) + random.random()
            time.sleep(wait)

    return None

# =========================
# SESSION CACHE (CRITICAL FIX)
# =========================

def get_data():

    if "cached_data" not in st.session_state:

        data = fetch_top_200_coingecko()

        if data:
            st.session_state.cached_data = data
            st.session_state.last_update = time.time()

    return st.session_state.get("cached_data", [])

# =========================
# REFRESH CONTROL (NO API SPAM)
# =========================

def should_refresh(interval=1800):  # 30 min safe default

    if "last_update" not in st.session_state:
        return True

    return (time.time() - st.session_state.last_update) > interval

# =========================
# FEATURE ENGINEERING
# =========================

def add_features(df):
    df = df.copy()

    df["volatility"] = ((df["high_24h"] - df["low_24h"]) / df["price"]) * 100
    df["liq_ratio"] = df["volume"] / df["market_cap"]

    df["trend_strength"] = (
        df["change_24h"] * 0.3 +
        df["change_7d"] * 0.5 +
        df["change_30d"] * 0.2
    )

    return df

# =========================
# SIGNAL ENGINE
# =========================

def generate_signal(row):

    score = 0
    signal = "HOLD"
    reasons = []

    if row["change_7d"] > 10:
        score += 30
        reasons.append("Strong 7D uptrend")

    elif row["change_7d"] < -10:
        score -= 30
        reasons.append("Strong 7D downtrend")

    if row["change_24h"] > 5:
        score += 20
        reasons.append("Positive 24H momentum")

    if row["change_24h"] < -5:
        score -= 20
        reasons.append("Negative 24H momentum")

    if row["volume"] > 1e9:
        score += 15
        reasons.append("High liquidity")

    if 3 < row["volatility"] < 12:
        score += 10
        reasons.append("Healthy volatility")

    elif row["volatility"] > 20:
        score -= 10
        reasons.append("Too volatile")

    if row["liq_ratio"] > 0.05:
        score += 20
        reasons.append("Strong liquidity ratio")

    elif row["liq_ratio"] < 0.01:
        score -= 10
        reasons.append("Weak liquidity")

    if score >= 50:
        signal = "BUY"
    elif score <= -30:
        signal = "SELL"

    return score, signal, reasons

# =========================
# LOAD DATA (SAFE)
# =========================

st.title("🚀 Crypto Trading System Pro (Production Stable)")

if should_refresh():
    data = fetch_top_200_coingecko()

    if data:
        st.session_state.cached_data = data
        st.session_state.last_update = time.time()

raw_data = get_data()

if not raw_data:
    st.warning("Using cached data or waiting for API recovery (rate limit safe mode)")
    st.stop()

df = pd.DataFrame(raw_data)
df = add_features(df)

results = df.apply(lambda row: generate_signal(row), axis=1)

df["score"] = [r[0] for r in results]
df["signal"] = [r[1] for r in results]
df["reasons"] = [", ".join(r[2]) for r in results]

df = df.sort_values("score", ascending=False)

# =========================
# SIDEBAR
# =========================

st.sidebar.title("Trading Filters")

signal_filter = st.sidebar.multiselect(
    "Signal Type",
    ["BUY", "SELL", "HOLD"],
    default=["BUY", "SELL"]
)

min_score = st.sidebar.slider("Min Score", -100, 100, -20)

auto = st.sidebar.checkbox("Auto Refresh (Safe Mode)")

df = df[
    (df["signal"].isin(signal_filter)) &
    (df["score"] >= min_score)
]

# =========================
# AUTO REFRESH (SAFE)
# =========================

if auto:
    st.sidebar.info("Safe refresh every 30 minutes (no API spam)")
    time.sleep(1800)
    st.rerun()

# =========================
# DASHBOARD
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Signals", len(df))

with col2:
    st.metric("Top Score", df["score"].max())

with col3:
    st.metric("Avg Score", round(df["score"].mean(), 2))

st.divider()

# =========================
# TABLE
# =========================

st.subheader("📊 Trading Signals")

st.dataframe(
    df[[
        "name", "symbol", "price",
        "change_24h", "change_7d", "change_30d",
        "volatility", "liq_ratio",
        "score", "signal", "reasons"
    ]],
    use_container_width=True
)

# =========================
# TOP TRADES
# =========================

st.subheader("🔥 Top Trade Setups")

for _, row in df.head(10).iterrows():

    color = "🟢" if row["signal"] == "BUY" else "🔴" if row["signal"] == "SELL" else "⚪"

    st.write(f"""
{color} **{row['name']} ({row['symbol']})**

Signal: **{row['signal']}**
Score: {row['score']}

Price: ${row['price']}
24H: {row['change_24h']:.2f}%
7D: {row['change_7d']:.2f}%

Reasons: {row['reasons']}
""")

# =========================
# STATUS
# =========================

st.sidebar.caption("API: CoinGecko | Mode: Production Stable | 429 Protected")
