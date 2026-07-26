import sqlite3
from datetime import datetime

class Brain:

    def __init__(self, db="learning.db"):
        self.conn = sqlite3.connect(db)

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS trades(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset TEXT,
            direction TEXT,
            timeframe INTEGER,
            confidence REAL,
            market_quality REAL,
            rsi REAL,
            adx REAL,
            atr REAL,
            bollinger_width REAL,
            score_buy REAL,
            score_sell REAL,
            result TEXT,
            profit REAL,
            created_at TEXT
        )
        """)

        self.conn.commit()

    def save(self, **k):

        self.conn.execute("""
        INSERT INTO trades(
            asset,
            direction,
            timeframe,
            confidence,
            market_quality,
            rsi,
            adx,
            atr,
            bollinger_width,
            score_buy,
            score_sell,
            result,
            profit,
            created_at
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,(
            k.get("asset"),
            k.get("direction"),
            k.get("timeframe"),
            k.get("confidence"),
            k.get("market_quality"),
            k.get("rsi"),
            k.get("adx"),
            k.get("atr"),
            k.get("bollinger_width"),
            k.get("score_buy"),
            k.get("score_sell"),
            k.get("result"),
            k.get("profit"),
            datetime.utcnow().isoformat()
        ))

        self.conn.commit()

print("🧠 Brain carregado.")
