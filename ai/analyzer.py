import sqlite3

conn = sqlite3.connect("learning.db")
conn.row_factory = sqlite3.Row

print("="*60)
print("BRAIN ANALYZER")
print("="*60)

total = conn.execute(
    "SELECT COUNT(*) FROM trades"
).fetchone()[0]

print("Trades:", total)

if total == 0:
    print("Ainda não existe histórico.")
    raise SystemExit

print("\nWIN RATE GERAL")

wins = conn.execute(
    "SELECT COUNT(*) FROM trades WHERE result='WIN'"
).fetchone()[0]

print(f"{wins}/{total} = {wins/total*100:.2f}%")

print("\nATIVOS")

for r in conn.execute("""
SELECT
asset,
COUNT(*) n,
ROUND(
100.0*SUM(result='WIN')/COUNT(*),2
)
FROM trades
GROUP BY asset
ORDER BY 3 DESC
"""):
    print(r[0], " Trades:", r[1], " Win:", r[2], "%")

print("\nMQ")

for r in conn.execute("""
SELECT
market_quality,
COUNT(*),
ROUND(
100.0*SUM(result='WIN')/COUNT(*),2
)
FROM trades
GROUP BY market_quality
ORDER BY market_quality
"""):
    print(r)

print("\nCONFIANÇA")

for r in conn.execute("""
SELECT
CAST(confidence/5 AS INT)*5 faixa,
COUNT(*),
ROUND(
100.0*SUM(result='WIN')/COUNT(*),2
)
FROM trades
GROUP BY faixa
ORDER BY faixa
"""):
    print(f"{r[0]}-{r[0]+4}% :",r[2],"%")

conn.close()
