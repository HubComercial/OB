#!/usr/bin/env python3

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "learning.db"

class Statistics:

    def __init__(self):
        self.conn = sqlite3.connect(DB)
        self.conn.row_factory = sqlite3.Row

    def total(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM trades"
        ).fetchone()[0]

    def win_rate(self):

        total = self.total()

        if total == 0:
            return 0

        wins = self.conn.execute(
            "SELECT COUNT(*) FROM trades WHERE result='WIN'"
        ).fetchone()[0]

        return round(wins * 100 / total,2)

    def best_assets(self):

        return self.conn.execute("""

        SELECT
            asset,
            COUNT(*) trades,
            ROUND(
                SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END)*100.0/
                COUNT(*),2
            ) win_rate

        FROM trades

        GROUP BY asset

        HAVING trades>=5

        ORDER BY win_rate DESC

        """).fetchall()


if __name__=="__main__":

    s=Statistics()

    print("="*50)
    print("AI STATISTICS")
    print("="*50)

    print("Trades :",s.total())
    print("WinRate:",s.win_rate(),"%")

    print("\nMelhores ativos\n")

    for a in s.best_assets():

        print(
            f"{a['asset']}  "
            f"{a['trades']} trades  "
            f"{a['win_rate']}%"
        )

