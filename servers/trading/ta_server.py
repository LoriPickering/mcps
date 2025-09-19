# server.py  — MCP server exposing indicator signals
import asyncio, json, time
from typing import Dict, Any, List, Literal
import pandas as pd
import pandas_ta as ta
from mcp.server.fastapi import FastAPIServer
from fastapi import FastAPI

# --- replace this with your data feed ---
# Example uses a simple ring buffer you fill via webhooks (e.g., TradingView -> http://localhost:8742/hook)
CANDLES: Dict[str, pd.DataFrame] = {}  # key "APPX-1m" -> DataFrame[time, open, high, low, close, volume]

api = FastAPI()
mcp = FastAPIServer(api, "chart-signals")

@api.post("/hook")
def hook(payload: Dict[str, Any]):
    # Expect payload: {"symbol":"APPX","tf":"1m","bar":{"t":..., "o":..., "h":..., "l":..., "c":..., "v":...}}
    sym, tf, bar = payload["symbol"], payload["tf"], payload["bar"]
    key = f"{sym}-{tf}"
    df = CANDLES.get(key, pd.DataFrame(columns=list("tohlcv")))
    row = pd.DataFrame([{
        "t": pd.to_datetime(bar["t"], unit="s"),
        "o": float(bar["o"]), "h": float(bar["h"]), "l": float(bar["l"]),
        "c": float(bar["c"]), "v": float(bar["v"])
    }])
    df = pd.concat([df, row], ignore_index=True).drop_duplicates(subset=["t"]).sort_values("t")
    CANDLES[key] = df.tail(3000)  # keep last N bars
    return {"ok": True}

@mcp.tool()
def get_signals(symbol: str, tf: Literal["1s","5s","1m","5m","15m","1h"]="1m") -> Dict[str, Any]:
    """Return latest indicators and crossed flags."""
    key = f"{symbol}-{tf}"
    if key not in CANDLES or len(CANDLES[key]) < 35:
        return {"ready": False, "reason": "insufficient bars"}
    df = CANDLES[key].copy().set_index("t")

    # Indicators
    df["ema9"]  = ta.ema(df["c"], length=9)
    df["ma10"]  = ta.sma(df["c"], length=10)
    macd = ta.macd(df["c"], fast=12, slow=26, signal=9)
    df["macd"], df["signal"], df["hist"] = macd["MACD_12_26_9"], macd["MACDs_12_26_9"], macd["MACDh_12_26_9"]
    df["rsi"]   = ta.rsi(df["c"], length=14)

    last, prev = df.iloc[-1], df.iloc[-2]
    crossings = {
        "macd_cross_up":  prev["macd"] <= prev["signal"] and last["macd"] > last["signal"],
        "macd_cross_dn":  prev["macd"] >= prev["signal"] and last["macd"] < last["signal"],
        "ema_support_lost": prev["c"] >= prev["ema9"] and last["c"] < last["ema9"],
        "ema_reclaim":      prev["c"] <= prev["ema9"] and last["c"] > last["ema9"],
        "rsi_overbought":   last["rsi"] >= 70,
        "rsi_oversold":     last["rsi"] <= 30,
    }
    snapshot = {
        "price": float(last["c"]), "ema9": float(last["ema9"]), "ma10": float(last["ma10"]),
        "macd": float(last["macd"]), "signal": float(last["signal"]), "hist": float(last["hist"]),
        "rsi": float(last["rsi"]), "time": str(df.index[-1])
    }
    return {"ready": True, "symbol": symbol, "tf": tf, "snapshot": snapshot, "crossings": crossings}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="127.0.0.1", port=8742)

