#!/usr/bin/env python3
import pandas as pd
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
import glob

REPO_DIR = os.path.expanduser("~/binary_signals_bot")
DASHBOARD_JSON = os.path.join(REPO_DIR, "dashboard.json")
FEEDBACK_CSV = os.path.join(REPO_DIR, "data/feedback.csv")
HISTORICAL_CSV = os.path.join(REPO_DIR, "data/analysis/historical_analysis.csv")

def get_uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            return float(f.read().split()[0])
    except:
        return 0

def get_system_health():
    try:
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
    except:
        cpu = ram = disk = 0
    uptime = get_uptime()
    reconnections = timeouts = yahoo_failures = 0
    try:
        with open(os.path.join(REPO_DIR, "logs/telemetry.log"), "r") as f:
            for line in f:
                if "Reconexão" in line: reconnections += 1
                if "Timeout" in line: timeouts += 1
                if "Yahoo" in line and "falhou" in line: yahoo_failures += 1
    except:
        pass
    return {
        "cpu": round(cpu, 1),
        "ram": round(ram, 1),
        "disk": round(disk, 1),
        "uptime": round(uptime),
        "reconnections": reconnections,
        "timeouts": timeouts,
        "yahoo_failures": yahoo_failures,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def load_feedback():
    if not os.path.isfile(FEEDBACK_CSV):
        return pd.DataFrame()
    df = pd.read_csv(FEEDBACK_CSV)
    return df

def load_historical():
    if not os.path.isfile(HISTORICAL_CSV):
        return pd.DataFrame()
    return pd.read_csv(HISTORICAL_CSV)

def compute_overview(df):
    today = datetime.now().strftime("%Y-%m-%d")
    df_today = df[df['timestamp'].str.startswith(today)] if not df.empty else pd.DataFrame()
    trades_today = len(df_today)
    wins = len(df_today[df_today['resultado'] == 'WIN'])
    losses = len(df_today[df_today['resultado'] == 'LOSS'])
    timeouts = len(df_today[df_today['resultado'] == 'TIMEOUT'])
    confirmed = wins + losses
    win_rate = (wins / confirmed * 100) if confirmed > 0 else 0
    df_all = df[df['resultado'].isin(['WIN', 'LOSS'])].copy()
    if not df_all.empty and 'pnl' in df_all.columns:
        total_profit = df_all[df_all['resultado'] == 'WIN']['pnl'].sum()
        total_loss = abs(df_all[df_all['resultado'] == 'LOSS']['pnl'].sum())
        net_profit = df_all['pnl'].sum()
        drawdown = df_all['pnl'].min() if not df_all.empty else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
    else:
        net_profit = wins * 0.8 - losses * 1.0
        drawdown = -losses if losses > 0 else 0
        profit_factor = (wins * 0.8) / (losses * 1.0) if losses > 0 else 0
    return {
        "trades_today": trades_today,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "drawdown": round(drawdown, 2),
        "net_profit": round(net_profit, 2)
    }

def compute_performance(df):
    if df.empty:
        return {"win_rate_by_asset": {}, "win_rate_by_hour": {}, "win_rate_by_weekday": [], "daily_pnl": []}
    df = df[df['resultado'].isin(['WIN', 'LOSS'])].copy()
    if df.empty:
        return {"win_rate_by_asset": {}, "win_rate_by_hour": {}, "win_rate_by_weekday": [], "daily_pnl": []}
    asset_wr = {}
    for asset in df['ativo'].unique():
        sub = df[df['ativo'] == asset]
        w = len(sub[sub['resultado'] == 'WIN'])
        total = len(sub)
        asset_wr[asset] = (w / total * 100) if total > 0 else 0
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    hour_wr = {}
    for hour in range(24):
        sub = df[df['hour'] == hour]
        if len(sub) > 0:
            w = len(sub[sub['resultado'] == 'WIN'])
            hour_wr[str(hour)] = (w / len(sub) * 100) if len(sub) > 0 else 0
    # dia da semana (0=segunda)
    df['weekday'] = pd.to_datetime(df['timestamp']).dt.weekday
    weekday_wr = []
    for wd in range(7):
        sub = df[df['weekday'] == wd]
        if len(sub) > 0:
            w = len(sub[sub['resultado'] == 'WIN'])
            weekday_wr.append((w / len(sub) * 100) if len(sub) > 0 else 0)
        else:
            weekday_wr.append(0)
    # daily P&L
    daily_pnl = []
    if 'pnl' in df.columns:
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        for date, group in df.groupby('date'):
            daily_pnl.append({"date": str(date), "pnl": round(group['pnl'].sum(), 2)})
    else:
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        for date, group in df.groupby('date'):
            wins_day = len(group[group['resultado'] == 'WIN'])
            losses_day = len(group[group['resultado'] == 'LOSS'])
            pnl = wins_day * 0.8 - losses_day * 1.0
            daily_pnl.append({"date": str(date), "pnl": round(pnl, 2)})
    return {
        "win_rate_by_asset": asset_wr,
        "win_rate_by_hour": hour_wr,
        "win_rate_by_weekday": weekday_wr,
        "daily_pnl": daily_pnl[-30:]
    }

def compute_brain(df_hist):
    if df_hist.empty:
        return {"signals_generated": 0, "signals_blocked": 0, "avg_mq": 0, "avg_adx": 0, "avg_atr": 0, "avg_confidence": 0}
    total = len(df_hist)
    blocked = 0
    if 'filters_blocked' in df_hist.columns:
        blocked = df_hist['filters_blocked'].apply(lambda x: 0 if pd.isna(x) or x == '[]' else 1).sum()
    generated = total - blocked
    avg_mq = df_hist['market_quality'].mean() if 'market_quality' in df_hist.columns else 0
    avg_adx = df_hist['adx'].mean() if 'adx' in df_hist.columns else 0
    avg_atr = df_hist['atr'].mean() if 'atr' in df_hist.columns else 0
    avg_confidence = df_hist['confidence'].mean() if 'confidence' in df_hist.columns else 0
    return {
        "signals_generated": generated,
        "signals_blocked": blocked,
        "avg_mq": round(avg_mq, 1),
        "avg_adx": round(avg_adx, 1),
        "avg_atr": round(avg_atr, 5),
        "avg_confidence": round(avg_confidence, 1)
    }

def compute_filters(df_hist):
    filter_counts = {"mq": 0, "adx": 0, "bollinger": 0, "score": 0}
    if df_hist.empty or 'filters_blocked' not in df_hist.columns:
        return filter_counts
    for _, row in df_hist.iterrows():
        blocked = row['filters_blocked']
        if pd.isna(blocked):
            continue
        if 'MQ' in blocked:
            filter_counts['mq'] += 1
        if 'ADX' in blocked:
            filter_counts['adx'] += 1
        if 'Bollinger' in blocked or 'BW' in blocked:
            filter_counts['bollinger'] += 1
        if 'Score' in blocked:
            filter_counts['score'] += 1
    return filter_counts

def compute_accuracy(df):
    if df.empty:
        return {}
    df = df[df['resultado'].isin(['WIN', 'LOSS'])].copy()
    if df.empty:
        return {}
    if 'confidence' in df.columns:
        bins = [0, 70, 80, 90, 101]
        labels = ['<70', '70-80', '80-90', '90-100']
        df['conf_group'] = pd.cut(df['confidence'], bins=bins, labels=labels, right=False)
    elif 'score_buy' in df.columns and 'score_sell' in df.columns:
        df['confidence'] = df[['score_buy', 'score_sell']].max(axis=1)
        bins = [0, 70, 80, 90, 101]
        labels = ['<70', '70-80', '80-90', '90-100']
        df['conf_group'] = pd.cut(df['confidence'], bins=bins, labels=labels, right=False)
    else:
        return {}
    result = {}
    for group in labels:
        sub = df[df['conf_group'] == group]
        if len(sub) > 0:
            w = len(sub[sub['resultado'] == 'WIN'])
            total = len(sub)
            result[group] = {"trades": total, "wins": w, "win_rate": round((w / total) * 100, 1)}
        else:
            result[group] = {"trades": 0, "wins": 0, "win_rate": 0}
    return result

def compute_history(df):
    if df.empty:
        return {"last_30_days": 0, "last_12_months": 0, "best_day": {"date": "", "pnl": 0}, "worst_day": {"date": "", "pnl": 0}, "max_win_streak": 0, "max_loss_streak": 0}
    df = df[df['resultado'].isin(['WIN', 'LOSS'])].copy()
    if df.empty:
        return {"last_30_days": 0, "last_12_months": 0, "best_day": {"date": "", "pnl": 0}, "worst_day": {"date": "", "pnl": 0}, "max_win_streak": 0, "max_loss_streak": 0}
    cutoff30 = (datetime.now() - timedelta(days=30)).isoformat()
    df30 = df[df['timestamp'] >= cutoff30]
    cutoff12 = (datetime.now() - timedelta(days=365)).isoformat()
    df12 = df[df['timestamp'] >= cutoff12]
    best_day = {"date": "", "pnl": 0}
    worst_day = {"date": "", "pnl": 0}
    if 'pnl' in df.columns:
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily = df.groupby('date')['pnl'].sum().reset_index()
        if not daily.empty:
            best = daily.loc[daily['pnl'].idxmax()]
            worst = daily.loc[daily['pnl'].idxmin()]
            best_day = {"date": str(best['date']), "pnl": round(best['pnl'], 2)}
            worst_day = {"date": str(worst['date']), "pnl": round(worst['pnl'], 2)}
    df_sorted = df.sort_values('timestamp')
    results = df_sorted['resultado'].tolist()
    max_win_streak = max_loss_streak = 0
    cw = cl = 0
    for r in results:
        if r == 'WIN':
            cw += 1
            cl = 0
            max_win_streak = max(max_win_streak, cw)
        else:
            cl += 1
            cw = 0
            max_loss_streak = max(max_loss_streak, cl)
    return {
        "last_30_days": len(df30),
        "last_12_months": len(df12),
        "best_day": best_day,
        "worst_day": worst_day,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak
    }

def compute_directions(df):
    if df.empty:
        return {"buy": 0, "sell": 0}
    df_dir = df[df['resultado'].isin(['WIN', 'LOSS', 'TIMEOUT'])].copy()
    buys = len(df_dir[df_dir['direction'] == 'COMPRA'])
    sells = len(df_dir[df_dir['direction'] == 'VENDA'])
    return {"buy": buys, "sell": sells}

def compute_avg_time(df):
    if df.empty:
        return 0
    df_sorted = df[df['resultado'].isin(['WIN', 'LOSS', 'TIMEOUT'])].sort_values('timestamp')
    if len(df_sorted) < 2:
        return 0
    times = pd.to_datetime(df_sorted['timestamp'])
    diffs = times.diff().dropna()
    avg_minutes = diffs.dt.total_seconds().mean() / 60
    return round(avg_minutes, 1)

def compute_last_trades(df, n=10):
    if df.empty:
        return []
    df_sorted = df.sort_values('timestamp', ascending=False).head(n)
    trades = []
    for _, row in df_sorted.iterrows():
        trades.append({
            "timestamp": row.get('timestamp', '')[:16],
            "asset": row.get('ativo', ''),
            "direction": row.get('direction', ''),
            "result": row.get('resultado', 'PENDENTE'),
            "pnl": round(row.get('pnl', 0), 2) if 'pnl' in row else 0
        })
    return trades

def main():
    print("📊 A gerar dashboard.json...")
    df_fb = load_feedback()
    df_hist = load_historical()

    data = {
        "overview": compute_overview(df_fb),
        "performance": compute_performance(df_fb),
        "brain": compute_brain(df_hist),
        "filters": compute_filters(df_hist),
        "accuracy": compute_accuracy(df_fb),
        "history": compute_history(df_fb),
        "directions": compute_directions(df_fb),
        "avg_time_between_trades": compute_avg_time(df_fb),
        "health": get_system_health(),
        "last_trades": compute_last_trades(df_fb)
    }

    with open(DASHBOARD_JSON, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ dashboard.json gerado.")
    try:
        os.chdir(REPO_DIR)
        subprocess.run(["git", "add", "dashboard.json"], check=True)
        subprocess.run(["git", "commit", "-m", f"Update dashboard {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ Push para GitHub efetuado.")
    except Exception as e:
        print(f"⚠️ Erro no git push: {e}")

if __name__ == "__main__":
    main()
