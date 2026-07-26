#!/usr/bin/env python3

import sqlite3
from pathlib import Path

db = Path("learning.db")

conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS trades (

id INTEGER PRIMARY KEY AUTOINCREMENT,

timestamp TEXT,

asset TEXT,

timeframe INTEGER,

direction TEXT,

entry_price REAL,

exit_price REAL,

result TEXT,

profit REAL,

confidence REAL,

market_quality REAL,

score_buy REAL,

score_sell REAL,

atr REAL,

adx REAL,

rsi REAL,

macd REAL,

cci REAL,

bollinger_width REAL,

volume_ratio REAL,

ema_fast REAL,

ema_trend REAL,

trend_direction TEXT

)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_asset
ON trades(asset)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_result
ON trades(result)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_timestamp
ON trades(timestamp)
""")

conn.commit()
conn.close()

print("="*60)
print("🧠 BANCO DE APRENDIZAGEM CRIADO")
print("Arquivo:", db.resolve())
print("="*60)
