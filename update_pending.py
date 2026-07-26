import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'database/strategy_learning.db'
FEEDBACK_PATH = 'data/feedback.csv'

def to_unix(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return int(dt.timestamp())
    except:
        return None

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    df = pd.read_csv(FEEDBACK_PATH)
except:
    print("⚠️ feedback.csv não encontrado.")
    exit()

df = df[df['result'].notna() & (df['result'] != 'PENDENTE')]
updated = 0
for _, row in df.iterrows():
    asset = row.get('asset')
    direction = row.get('direction')
    timestamp_str = row.get('timestamp')
    result = row.get('result')
    exit_price = row.get('exit_price')
    if not all([asset, direction, timestamp_str]):
        continue
    ts = to_unix(timestamp_str)
    if ts is None:
        continue
    cursor.execute('''
        SELECT id FROM market_context
        WHERE asset = ? AND direction = ? AND timestamp = ? AND result = 'PENDENTE'
        ORDER BY id DESC LIMIT 1
    ''', (asset, direction, ts))
    row_db = cursor.fetchone()
    if row_db:
        cursor.execute('''
            UPDATE market_context
            SET result = ?, exit_price = ?
            WHERE id = ?
        ''', (result, exit_price, row_db[0]))
        updated += 1
conn.commit()
conn.close()
print(f"✅ {updated} registos PENDENTE atualizados.")
