"""
modules/execution.py
Simula a execução de ordens de compra/venda.
Por enquanto, usa um sorteio aleatório para simular o resultado.
"""
import time
import random
import logging

class OrderExecutor:
    def __init__(self, min_interval=16):
        """
        :param min_interval: Intervalo mínimo entre trades (em segundos)
        """
        self.last_trade_time = 0
        self.min_interval = min_interval
        print(f"📟 Executor inicializado. Intervalo mínimo: {min_interval}s")
    
    def execute_signal(self, signal: str, asset: str, amount: float, expiry: int):
        """
        Executa uma ordem.
        Retorna True se ganhou, False se perdeu, ou None se não executou (ex: intervalo).
        """
        if signal not in ["COMPRA", "VENDA"]:
            return None
        
        # Verifica intervalo mínimo entre trades
        now = time.time()
        if now - self.last_trade_time < self.min_interval:
            print(f"⏳ Aguardando intervalo mínimo de {self.min_interval}s...")
            return None
        
        # Define a direção (Call = COMPRA, Put = VENDA)
        direction = "CALL" if signal == "COMPRA" else "PUT"
        print(f"📊 Executando {direction} em {asset} no valor de ${amount:.2f} (expira em {expiry}s)")
        
        # ===== SIMULAÇÃO DO RESULTADO =====
        # Aqui depois entraremos com a API real da PocketOption
        # Por enquanto, 60% de chance de ganhar (para testes)
        win = random.random() < 0.60
        
        self.last_trade_time = now
        
        if win:
            print(f"✅ Ordem GANHOU!")
        else:
            print(f"❌ Ordem PERDEU!")
        
        return winx
