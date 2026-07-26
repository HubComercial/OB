from datetime import datetime

def should_use_otc():
    """Desativado permanentemente – apenas mercado normal."""
    return False
def should_use_backtest():
    """
    Determina se o robô deve rodar o backtest em vez de operar ao vivo.
    True se for fim de semana e BACKTEST_WEEKEND estiver ativo.
    """
    from config import BACKTEST_WEEKEND
    if not BACKTEST_WEEKEND:
        return False
    now = datetime.now()
    # Fim de semana ou horário específico (ex: madrugada)
    if now.weekday() in [5, 6]:
        return True
    # Opção: rodar backtest também em dias úteis na madrugada (ex: 2h-5h)
    # if now.hour >= 2 and now.hour < 5:
    #     return True
    return False
