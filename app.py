import streamlit as st
import pandas as pd
import numpy as np
import websocket
import json
import threading
import time

# =========================
# CONFIG
# =========================

st.set_page_config(
    page_title="Live Crypto Trading System",
    layout="wide"
)

# =========================
# LIVE DATA STORE
# =========================

if "live_data" not in st.session_state:
    st.session_state.live_data = {}

# =========================
# BINANCE WEBSOCKET STREAM
# =========================

SYMBOLS = [
    "btcusdt",
    "ethusdt",
    "solusdt",
    "bnbusdt",
    "xrpusdt"
]

STREAM_URL = "wss://stream.binance.com:9443/stream?streams=" + "/".join(
    [f"{s}@ticker" for s in SYMBOLS]
)

# =========================
# WEBSOCKET CALLBACKS
# =========================

def on_message(ws, message):
    data = json.loads(message)

    ticker = data["data"]
    symbol = ticker["s"]

    st.session_state.live_data[symbol] = {
        "price": float(ticker["c"]),
        "change_24h": float(ticker["P"]),
        "volume": float(ticker["v"]),
        "high": float(ticker["h"]),
        "low": float(ticker["l"])
    }

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")

def on_open(ws):
    print("WebSocket connected")

# =========================
# START WEBSOCKET THREAD
# =========================

def start_ws():
    ws = websocket.WebSocketApp(
        STREAM_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever()

if "ws_started" not in st.session_state:
    thread = threading.Thread(target=start_ws, daemon=True)
    thread.start()
    st.session_state.ws_started = True

# =========================
# SIGNAL ENGINE
# =========================

def generate_signal(row):

    score = 0
    signal = "HOLD"
    reasons = []

    if row["change_24h"] > 2:
        score += 20
        reasons.append("Positive momentum")

    if row["change_24h"] < -2:
        score -= 20
        reasons.append("Negative momentum")

    if row["volume"] > 1e6:
        score += 10
        reasons.append("High volume")

    if score >= 25:
        signal = "BUY"
    elif score <= -20:
        signal = "SELL"

    return score, signal, reasons

# =========================
# BUILD DATAFRAME
# =========================

def build_df():
    rows = []

    for symbol, data in st.session_state.live_data.items():

        rows.append({
            "symbol": symbol,
            "price": data["price"],
            "change_24h": data["change_24h"],
            "volume": data["volume"],
            "high": data["high"],
            "low": data["low"]
        })

    return pd.DataFrame(rows)

# =========================
# UI
# =========================

st.title("🚀 LIVE Crypto Trading System (WebSocket)")

df = build_df()

if df.empty:
    st.warning("Waiting for live WebSocket data...")
    st.stop()

results = df.apply(lambda row: generate_signal(row), axis=1)

df["score"] = [r[0] for r in results]
df["signal"] = [r[1] for r in results]
df["reasons"] = [", ".join(r[2]) for r in results]

# =========================
# DASHBOARD
# =========================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Assets", len(df))

with col2:
    st.metric("Top Score", df["score"].max())

with col3:
    st.metric("Avg Change", round(df["change_24h"].mean(), 2))

st.divider()

# =========================
# TABLE
# =========================

st.dataframe(df, use_container_width=True)

# =========================
# TOP SETUPS
# =========================

st.subheader("🔥 Live Trade Signals")

for _, row in df.iterrows():

    color = "🟢" if row["signal"] == "BUY" else "🔴" if row["signal"] == "SELL" else "⚪"

    st.write(f"""
{color} **{row['symbol']}**

Price: {row['price']}
24h: {row['change_24h']}%
Score: {row['score']}
Signal: {row['signal']}
""")

# =========================
# AUTO REFRESH UI LOOP
# =========================

time.sleep(2)
st.rerun()
