#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.market_regime import detect_regime_change
from modules.notifier import send_telegram_message

def main():
    changed, diff, short, long = detect_regime_change()
    if changed:
        msg = f"⚠️ MUDANÇA DE REGIME DETETADA\n"
        msg += f"Últimos 100 trades: {short:.2f}%\n"
        msg += f"Últimos 300 trades: {long:.2f}%\n"
        msg += f"Diferença: {diff:.2f}%"
        send_telegram_message(msg)
    else:
        print("✅ Sem mudança de regime.")

if __name__ == "__main__":
    main()
