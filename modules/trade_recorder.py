"""
modules/trade_recorder.py
Registra todas as operações em CSV e calcula métricas de performance.
"""
import pandas as pd
import os
from datetime import datetime

class TradeRecorder:
    def __init__(self, filename="data/trades.csv"):
        self.filename = filename
        # Cria a pasta 'data' se não existir
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Se o arquivo não existir, cria com cabeçalho
        if not os.path.isfile(filename):
            df = pd.DataFrame(columns=[
                "Data", "Hora", "Ativo", "Direcao", "Valor", 
                "Resultado", "P&L", "P&L_Acumulado", "Acertos_Consecutivos"
            ])
            df.to_csv(filename, index=False)
    
    def add_trade(self, asset, direction, amount, result, pnl, consecutive_wins):
        """
        Adiciona um trade ao histórico.
        :param result: True se ganhou, False se perdeu
        :param pnl: Valor do lucro/perda em dólares
        """
        now = datetime.now()
        data = {
            "Data": now.strftime("%Y-%m-%d"),
            "Hora": now.strftime("%H:%M:%S"),
            "Ativo": asset,
            "Direcao": direction,
            "Valor": amount,
            "Resultado": "WIN" if result else "LOSS",
            "P&L": round(pnl, 2),
            "P&L_Acumulado": None,  # Preenchido depois
            "Acertos_Consecutivos": consecutive_wins
        }
        
        df = pd.read_csv(self.filename)
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        
        # Atualiza o P&L acumulado
        df['P&L_Acumulado'] = df['P&L'].cumsum()
        
        df.to_csv(self.filename, index=False)
        print(f"📝 Trade registrado em {self.filename}")
    
    def get_performance_summary(self):
        """Retorna um dicionário com as métricas de performance."""
        if not os.path.isfile(self.filename):
            return None
        
        df = pd.read_csv(self.filename)
        if len(df) == 0:
            return None
        
        total_trades = len(df)
        wins = len(df[df['Resultado'] == 'WIN'])
        losses = total_trades - wins
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        total_profit = df[df['Resultado'] == 'WIN']['P&L'].sum()
        total_loss = abs(df[df['Resultado'] == 'LOSS']['P&L'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        net_profit = df['P&L'].sum()
        avg_profit = df['P&L'].mean()
        
        # Calcula drawdown máximo (queda do pico)
        df['Pico'] = df['P&L_Acumulado'].cummax()
        df['Drawdown'] = df['Pico'] - df['P&L_Acumulado']
        max_drawdown = df['Drawdown'].max()
        
        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "net_profit": net_profit,
            "avg_profit": avg_profit,
            "max_drawdown": max_drawdown
        }
