import streamlit as st
import pandas as pd
import requests
import numpy as np

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="Crypto Trading System Pro",
    layout="wide"
)

# =========================
# DATA FETCH
# =========================

import time
import random

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

    for attempt in range(5):  # retry 5 times
        r = requests.get(url, params=params, headers=headers)

        if r.status_code == 200:
            data = r.json()

            if isinstance(data, list):
                return data

        if r.status_code == 429:
            wait = (2 ** attempt) + random.random()
            time.sleep(wait)
            continue

        break

    st.error("CoinGecko rate limit hit (429). Try again in a few seconds.")
    return []
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
# SIGNAL ENGINE (CORE TRADING LOGIC)
# =========================

def generate_signal(row):

    score = 0
    signal = "HOLD"
    reasons = []

    # -------------------------
    # TREND CHECK
    # -------------------------

    if row["change_7d"] > 10:
        score += 30
        reasons.append("Strong 7D uptrend")

    elif row["change_7d"] < -10:
        score -= 30
        reasons.append("Strong 7D downtrend")

    # -------------------------
    # MOMENTUM
    # -------------------------

    if row["change_24h"] > 5:
        score += 20
        reasons.append("Positive 24H momentum")

    if row["change_24h"] < -5:
        score -= 20
        reasons.append("Negative 24H momentum")

    # -------------------------
    # VOLUME CONFIRMATION
    # -------------------------

    if row["volume"] > 1e9:
        score += 15
        reasons.append("High liquidity")

    # -------------------------
    # VOLATILITY FILTER (avoid chaos)
    # -------------------------

    if 3 < row["volatility"] < 12:
        score += 10
        reasons.append("Healthy volatility")

    elif row["volatility"] > 20:
        score -= 10
        reasons.append("Too volatile")

    # -------------------------
    # LIQUIDITY QUALITY
    # -------------------------

    if row["liq_ratio"] > 0.05:
        score += 20
        reasons.append("Strong liquidity ratio")

    elif row["liq_ratio"] < 0.01:
        score -= 10
        reasons.append("Weak liquidity")

    # -------------------------
    # FINAL SIGNAL RULES
    # -------------------------

    if score >= 50:
        signal = "BUY"

    elif score <= -30:
        signal = "SELL"

    else:
        signal = "HOLD"

    return score, signal, reasons

# =========================
# LOAD DATA
# =========================

st.title("🚀 Crypto Trading System Pro (Signal Engine)")

df = fetch_top_200_coingecko()

if df.empty:
    st.stop()

df = add_features(df)

# apply signal engine
results = df.apply(lambda row: generate_signal(row), axis=1)

df["score"] = [r[0] for r in results]
df["signal"] = [r[1] for r in results]
df["reasons"] = [", ".join(r[2]) for r in results]

df = df.sort_values("score", ascending=False)

# =========================
# FILTERS
# =========================

st.sidebar.title("Trading Filters")
st.sidebar.caption("API status: CoinGecko live")

signal_filter = st.sidebar.multiselect(
    "Signal Type",
    ["BUY", "SELL", "HOLD"],
    default=["BUY", "SELL"]
)

min_score = st.sidebar.slider("Min Score", -100, 100, -20)

df = df[
    (df["signal"].isin(signal_filter)) &
    (df["score"] >= min_score)
]

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
# SIGNAL TABLE
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
# AUTO REFRESH
# =========================

auto = st.sidebar.checkbox("Auto Refresh (300s)")

if auto:
    st.sidebar.info("Live mode enabled")
    st.cache_data.clear()
    st.rerun()
