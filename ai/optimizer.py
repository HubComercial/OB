import sqlite3

class Optimizer:
    def __init__(self, db="learning.db"):
        self.conn = sqlite3.connect(db)

    def best_assets(self):
        cur = self.conn.execute("""
        SELECT asset,
               COUNT(*) total,
               SUM(result='WIN') wins,
               ROUND(100.0*SUM(result='WIN')/COUNT(*),2) wr
        FROM trades
        GROUP BY asset
        HAVING total>=5
        ORDER BY wr DESC
        """)
        return cur.fetchall()

    def best_confidence(self):
        cur = self.conn.execute("""
        SELECT CAST(confidence/5 AS INT)*5 faixa,
               COUNT(*) total,
               ROUND(100.0*SUM(result='WIN')/COUNT(*),2) wr
        FROM trades
        GROUP BY faixa
        HAVING total>=5
        ORDER BY faixa
        """)
        return cur.fetchall()

if __name__ == "__main__":
    o = Optimizer()

    print("\n===== MELHORES ATIVOS =====")
    for r in o.best_assets():
        print(r)

    print("\n===== WIN RATE POR CONFIANÇA =====")
    for r in o.best_confidence():
        print(r)
