#!/usr/bin/env python3
import sys
import os
import sqlite3
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = 'database/strategy_learning.db'

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def check_database():
    print_header("📊 1. BASE DE DADOS")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM market_context")
    total = cursor.fetchone()[0]
    print(f"  Total de registos: {total}")
    
    cursor.execute("SELECT COUNT(*) FROM market_context WHERE result != 'PENDENTE'")
    confirmed = cursor.fetchone()[0]
    print(f"  Confirmados (WIN/LOSS/EMPATE): {confirmed}")
    
    if confirmed > 0:
        cursor.execute("""
            SELECT result, COUNT(*) FROM market_context 
            WHERE result != 'PENDENTE' 
            GROUP BY result
        """)
        for r, c in cursor.fetchall():
            print(f"    {r}: {c}")
    
    cursor.execute("""
        SELECT id, asset, direction, result, session, hour 
        FROM market_context 
        ORDER BY id DESC LIMIT 5
    """)
    print("\n  Últimos 5 registos:")
    for row in cursor.fetchall():
        print(f"    ID:{row[0]} {row[1]} {row[2]} → {row[3]} ({row[4]} {row[5]}h)")
    
    conn.close()
    return confirmed

def run_dashboard():
    print_header("📊 2. DASHBOARD")
    try:
        from modules.dashboard import show_dashboard
        show_dashboard()
    except Exception as e:
        print(f"  ❌ Erro ao executar dashboard: {e}")

def run_investigator():
    print_header("📊 3. INVESTIGADOR")
    try:
        from modules.investigator import generate_report
        generate_report()
    except Exception as e:
        print(f"  ❌ Erro ao executar investigador: {e}")

def run_regime():
    print_header("📊 4. DETETOR DE REGIME")
    try:
        from modules.market_regime import generate_regime_report
        generate_regime_report()
    except Exception as e:
        print(f"  ❌ Erro ao executar regime: {e}")

def run_blacklist():
    print_header("📊 5. BLACKLIST (se houver dados)")
    try:
        from modules.blacklist_manager import update_blacklist
        updated = update_blacklist(min_trades=30, max_win_rate=40.0)
        if updated == 0:
            print("  ℹ️  Nenhum contexto com win_rate < 40% e 30+ trades.")
    except Exception as e:
        print(f"  ❌ Erro ao executar blacklist: {e}")

def run_priorities():
    print_header("📊 6. CONTEXTOS PREFERIDOS")
    try:
        from modules.context_priorities import update_priorities
        updated = update_priorities(min_trades=50, min_win_rate=65.0)
        if updated == 0:
            print("  ℹ️  Nenhum contexto com win_rate >= 65% e 50+ trades.")
    except Exception as e:
        print(f"  ❌ Erro ao executar prioridades: {e}")

def run_weights():
    print_header("📊 7. AJUSTE DE PESOS")
    try:
        from modules.dynamic_scorer import get_weight_recommendations
        suggestions = get_weight_recommendations()
        if suggestions:
            print("  ✅ Sugestões disponíveis.")
        else:
            print("  ℹ️  Dados insuficientes (mínimo 10 trades).")
    except Exception as e:
        print(f"  ❌ Erro ao executar weights: {e}")

def main():
    print("\n🔍 DIAGNÓSTICO COMPLETO DO ROBÔ")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    confirmed = check_database()
    
    if confirmed >= 1:
        run_dashboard()
        run_investigator()
        run_regime()
    else:
        print("\n⚠️  Ainda não há trades confirmados. Os módulos de análise aguardam dados.")
    
    if confirmed >= 10:
        run_weights()
    else:
        print(f"\n⏳  Para análise de pesos: {confirmed}/10 trades confirmados.")
    
    if confirmed >= 30:
        run_blacklist()
    else:
        print(f"⏳  Para blacklist: {confirmed}/30 trades confirmados.")
    
    if confirmed >= 50:
        run_priorities()
    else:
        print(f"⏳  Para prioridades: {confirmed}/50 trades confirmados.")
    
    print("\n" + "=" * 70)
    print("✅ DIAGNÓSTICO CONCLUÍDO")
    print("=" * 70)

if __name__ == "__main__":
    main()
