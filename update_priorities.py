#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.context_priorities import update_priorities

if __name__ == "__main__":
    print("🔄 Atualizando grupos prioritários...")
    updated = update_priorities(min_trades=50, min_win_rate=65.0)
    if updated > 0:
        print("✅ Prioridades atualizadas com sucesso.")
    else:
        print("ℹ️ Nenhum novo grupo prioritário identificado.")
