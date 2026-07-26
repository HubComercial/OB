import sqlite3
import pandas as pd
import json
from datetime import datetime
from modules.context_analyzer import analyze_groups
from modules.dynamic_scorer import calculate_indicator_importance, load_current_weights
from modules.temporal_learner import get_best_hours, get_worst_hours, get_session_win_rate
from modules.asset_ranker import get_top_assets, get_bottom_assets

DB_PATH = 'database/strategy_learning.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def generate_report():
    """Gera um relatório completo com recomendações."""
    print("\n" + "=" * 70)
    print("📋 RELATÓRIO DO INVESTIGADOR")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    
    conn = get_connection()
    
    # 1. Estatísticas gerais
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses
        FROM market_context
        WHERE result != 'PENDENTE'
    ''')
    row = cursor.fetchone()
    total, wins, losses = row
    win_rate = (wins / total * 100) if total > 0 else 0.0
    
    if total == 0:
        print("\n⚠️ Ainda não há trades confirmados. Volte a executar após alguns trades.")
        conn.close()
        return
    
    print(f"\n📊 RESUMO GERAL:")
    print(f"  Total de trades: {total}")
    print(f"  Vitórias: {wins}")
    print(f"  Derrotas: {losses}")
    print(f"  Win Rate: {win_rate:.2f}%")
    
    # 2. Análise de grupos
    print("\n" + "-" * 70)
    print("📊 ANÁLISE DE CONTEXTOS (grupos com >=3 trades):")
    df_groups = analyze_groups()
    if not df_groups.empty and not df_groups[df_groups['total'] >= 3].empty:
        df_filtered = df_groups[df_groups['total'] >= 3]
        for _, row in df_filtered.iterrows():
            print(f"  MQ:{row['mq_group']}, ADX:{row['adx_group']}, BW:{row['bw_group']} → {row['win_rate']:.2f}% ({row['total']} trades) [{row['classificacao']}]")
    else:
        print("  ⚠️ Ainda não há grupos com 3+ trades.")
    
    # 3. Indicadores mais influentes (correlação)
    print("\n" + "-" * 70)
    print("📊 INDICADORES MAIS INFLUENTES:")
    importance, msg = calculate_indicator_importance(min_trades=5)
    if importance:
        sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        for ind, val in sorted_imp[:5]:
            print(f"  {ind}: {val:.2f}% de influência")
    else:
        print(f"  ⚠️ {msg}")
    
    # 4. Análise temporal
    print("\n" + "-" * 70)
    print("🕒 ANÁLISE TEMPORAL:")
    best_hours = get_best_hours(min_trades=3, min_win_rate=60)
    if best_hours:
        hours_str = ', '.join([f"{h['hour']}h" for h in best_hours])
        print(f"  Melhores horas: {hours_str}")
    else:
        print("  ⚠️ Ainda sem horas com dados suficientes.")
    
    worst_hours = get_worst_hours(min_trades=3, max_win_rate=40)
    if worst_hours:
        hours_str = ', '.join([f"{h['hour']}h" for h in worst_hours])
        print(f"  Piores horas: {hours_str}")
    
    df_session = get_session_win_rate(min_trades=3)
    if not df_session.empty:
        print("  Win Rate por sessão:")
        for _, row in df_session.iterrows():
            print(f"    {row['session']}: {row['win_rate']:.2f}% ({row['wins']}/{row['total']})")
    else:
        print("  ⚠️ Dados insuficientes para análise por sessão.")
    
    # 5. Ranking por ativo
    print("\n" + "-" * 70)
    print("📊 RANKING POR ATIVO:")
    top_assets = get_top_assets(min_trades=3, min_win_rate=60)
    if top_assets:
        print("  ✅ Top ativos:")
        for a in top_assets:
            print(f"    {a['asset']}: {a['win_rate']:.2f}% ({a['wins']}/{a['total']})")
    else:
        print("  ⚠️ Ainda sem ativos com dados suficientes.")
    
    bottom_assets = get_bottom_assets(min_trades=3, max_win_rate=40)
    if bottom_assets:
        print("  ❌ Bottom ativos:")
        for a in bottom_assets:
            print(f"    {a['asset']}: {a['win_rate']:.2f}% ({a['wins']}/{a['total']})")
    
    # 6. Recomendações automáticas
    print("\n" + "-" * 70)
    print("💡 RECOMENDAÇÕES:")
    recommendations = []
    
    if win_rate < 45 and total > 10:
        recommendations.append("⚠️ Win Rate baixo (<45%). Considere aumentar SCORE_MIN para 85 ou reduzir BW_MIN para 0.00015.")
    elif win_rate > 60 and total > 10:
        recommendations.append("✅ Win Rate bom (>60%). Mantenha os filtros atuais ou aumente ligeiramente a agressividade.")
    
    # Recomendação por ativo
    if top_assets:
        recommendations.append(f"🏆 Priorize ativos: {', '.join([a['asset'] for a in top_assets[:3]])}")
    if bottom_assets:
        recommendations.append(f"📉 Evite ativos: {', '.join([a['asset'] for a in bottom_assets[:3]])}")
    
    for rec in recommendations:
        print(f"  {rec}")
    
    # 7. Contextos a bloquear (blacklist)
    print("\n" + "-" * 70)
    print("🚫 CONTEXTOS CANDIDATOS A BLACKLIST (win_rate < 40% e total >= 3):")
    if not df_groups.empty:
        blacklist = df_groups[(df_groups['total'] >= 3) & (df_groups['win_rate'] < 40)]
        if not blacklist.empty:
            for _, row in blacklist.iterrows():
                print(f"  MQ:{row['mq_group']}, ADX:{row['adx_group']}, BW:{row['bw_group']} → {row['win_rate']:.2f}% ({row['total']} trades)")
        else:
            print("  ✅ Nenhum contexto com win_rate < 40% e dados suficientes.")
    else:
        print("  ⚠️ Dados insuficientes para identificar contextos.")
    
    # 8. Contextos recomendados
    print("\n" + "-" * 70)
    print("✅ CONTEXTOS RECOMENDADOS (win_rate >= 65% e total >= 3):")
    if not df_groups.empty:
        recomendados = df_groups[(df_groups['total'] >= 3) & (df_groups['win_rate'] >= 65)]
        if not recomendados.empty:
            for _, row in recomendados.iterrows():
                print(f"  MQ:{row['mq_group']}, ADX:{row['adx_group']}, BW:{row['bw_group']} → {row['win_rate']:.2f}% ({row['total']} trades)")
        else:
            print("  ⚠️ Nenhum contexto com win_rate >= 65% e dados suficientes.")
    else:
        print("  ⚠️ Dados insuficientes.")
    
    conn.close()
    print("\n" + "=" * 70)
    print("🔍 Fim do relatório. Guarde estas recomendações para referência.")
    print("=" * 70)

if __name__ == "__main__":
    generate_report()
