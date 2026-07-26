#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.blacklist_manager import update_blacklist

if __name__ == "__main__":
    print("🚫 Atualizando blacklist...")
    updated = update_blacklist(min_trades=30, max_win_rate=40.0)
    print(f"✅ Blacklist atualizada: {updated} contextos bloqueados.")
