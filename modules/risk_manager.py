"""
modules/risk_manager.py
Gerencia o risco do robô: controle de perdas consecutivas e limite diário.
"""
from datetime import datetime

class RiskManager:
    def __init__(self, daily_loss_limit: float, max_consecutive_losses: int):
        """
        :param daily_loss_limit: Limite de perda diária (ex: -10.0 significa -$10)
        :param max_consecutive_losses: Máximo de perdas seguidas antes de pausar
        """
        self.daily_loss_limit = daily_loss_limit
        self.max_consecutive_losses = max_consecutive_losses
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.is_paused = False
        self.current_date = datetime.now().date()  # Para resetar automaticamente no novo dia
        
    def record_trade_result(self, win: bool, profit: float):
        """
        Registra o resultado de um trade.
        :param win: True se ganhou, False se perdeu
        :param profit: Lucro (positivo) ou prejuízo (negativo) em dólares
        """
        # Verifica se mudou de dia para resetar os contadores
        today = datetime.now().date()
        if today != self.current_date:
            self.reset_daily()
            self.current_date = today
        
        if win:
            self.consecutive_losses = 0
            self.daily_pnl += profit
            print(f"✅ Ganhou! P&L: +${profit:.2f}")
        else:
            self.consecutive_losses += 1
            self.daily_pnl -= abs(profit)  # profit é negativo aqui, então subtraímos o módulo
            print(f"❌ Perdeu! P&L: -${abs(profit):.2f}")
        
        # Verifica se atingiu o limite de perdas consecutivas
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.is_paused = True
            print(f"⛔ PAUSADO: {self.max_consecutive_losses} perdas consecutivas!")
        
        # Verifica se atingiu o limite diário de perda
        if self.daily_pnl <= self.daily_loss_limit:
            self.is_paused = True
            print(f"⛔ PAUSADO: Limite diário de perda atingido (${self.daily_pnl:.2f})")
    
    def can_trade(self) -> bool:
        """Retorna True se o robô pode operar, False se está pausado."""
        # Se mudou de dia, reseta automaticamente
        today = datetime.now().date()
        if today != self.current_date:
            self.reset_daily()
            self.current_date = today
        return not self.is_paused
    
    def reset_daily(self):
        """Reseta os contadores diários (chamado automaticamente ao mudar de dia)."""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.is_paused = False
        print("🔄 Contadores diários resetados!")
