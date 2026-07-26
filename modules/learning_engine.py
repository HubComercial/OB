import sqlite3
from datetime import datetime
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent.parent / "learning.db"

class LearningEngine:

    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

    def save_trade(self, **trade):

        self.cur.execute("""
        INSERT INTO trades(
            timestamp,
            asset,
            timeframe,
            direction,
            entry_price,
            exit_price,
            result,
            profit,
            confidence,
            market_quality,
            score_buy,
            score_sell,
            atr,
            adx,
            rsi,
            macd,
            cci,
            bollinger_width,
            volume_ratio,
            ema_fast,
            ema_trend,
            trend_direction
        )
        VALUES(
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?,?,?,
            ?,?
        )
        """, (

            trade.get("timestamp", datetime.utcnow().isoformat()),

            trade.get("asset"),

            trade.get("timeframe"),

            trade.get("direction"),

            trade.get("entry_price"),

            trade.get("exit_price"),

            trade.get("result"),

            trade.get("profit"),

            trade.get("confidence"),

            trade.get("market_quality"),

            trade.get("score_buy"),

            trade.get("score_sell"),

            trade.get("atr"),

            trade.get("adx"),

            trade.get("rsi"),

            trade.get("macd"),

            trade.get("cci"),

            trade.get("bollinger_width"),

            trade.get("volume_ratio"),

            trade.get("ema_fast"),

            trade.get("ema_trend"),

            trade.get("trend_direction")

        ))

        self.conn.commit()

    def total_trades(self):

        self.cur.execute("SELECT COUNT(*) total FROM trades")
        return self.cur.fetchone()["total"]

    def wins(self):

        self.cur.execute("SELECT COUNT(*) total FROM trades WHERE result='WIN'")
        return self.cur.fetchone()["total"]

    def losses(self):

        self.cur.execute("SELECT COUNT(*) total FROM trades WHERE result='LOSS'")
        return self.cur.fetchone()["total"]

    def win_rate(self):

        total = self.total_trades()

        if total == 0:
            return 0

        return round(self.wins() * 100 / total, 2)

    def close(self):
        self.conn.close()

if __name__ == "__main__":

    ai = LearningEngine()

    print("="*60)
    print("🧠 LEARNING ENGINE")
    print("="*60)
    print("Banco:", DB_FILE)
    print("Trades:", ai.total_trades())
    print("Wins:", ai.wins())
    print("Losses:", ai.losses())
    print("Win Rate:", ai.win_rate(), "%")
    print("="*60)

    ai.close()
