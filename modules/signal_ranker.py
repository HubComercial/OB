import pandas as pd
import numpy as np
from modules.context_priorities import get_priority_for_context
from modules.blacklist_manager import is_blocked

def rank_signals(signals, top_n=1):
    """
    Recebe uma lista de sinais (cada um um dicionário com:
        asset, timeframe, signal_data (contém signal, score_buy, score_sell, etc.),
        confidence, market_quality, entry_price, df
    )
    Retorna os top_n sinais ordenados por confiança (com prioridade de contexto aplicada).
    """
    print(f"\n[DEBUG] rank_signals recebeu {len(signals)} sinais.")
    
    if not signals:
        print("[DEBUG] Lista vazia. A retornar [].")
        return []
    
    if signals:
        print(f"[DEBUG] Exemplo de sinal: {signals[0].keys()}")
    
    # Filtrar sinais bloqueados pela blacklist
    original_len = len(signals)
    signals = [s for s in signals if not is_blocked(
        s.get('market_quality', 0),
        s.get('adx', 0),
        s.get('bollinger_width', 0)
    )]
    print(f"[DEBUG] Após blacklist: {len(signals)} de {original_len} sinais.")
    
    ranked = []
    for idx, s in enumerate(signals):
        # Extrair direção de várias fontes possíveis
        direction = None
        
        # 1. Tentar obter diretamente
        if 'direction' in s:
            direction = s['direction']
        # 2. Tentar de 'signal_data'
        elif 'signal_data' in s and isinstance(s['signal_data'], dict):
            direction = s['signal_data'].get('signal')
        # 3. Tentar de 'signal' (se existir diretamente)
        elif 'signal' in s:
            direction = s['signal']
        
        # Se ainda for None, tentar inferir pelos scores
        if direction is None:
            # Tentar scores de signal_data
            if 'signal_data' in s and isinstance(s['signal_data'], dict):
                sd = s['signal_data']
                score_buy = sd.get('score_buy', 0)
                score_sell = sd.get('score_sell', 0)
            else:
                score_buy = s.get('score_buy', 0)
                score_sell = s.get('score_sell', 0)
            
            if score_buy > score_sell:
                direction = 'COMPRA'
                print(f"[DEBUG] Sinal {idx}: inferido COMPRA para {s.get('asset')} (score_buy={score_buy})")
            elif score_sell > score_buy:
                direction = 'VENDA'
                print(f"[DEBUG] Sinal {idx}: inferido VENDA para {s.get('asset')} (score_sell={score_sell})")
            else:
                print(f"[DEBUG] Sinal {idx}: sem direção e scores iguais. Ignorado.")
                continue
        
        print(f"[DEBUG] Sinal {idx}: asset={s.get('asset')}, direction={direction}")
        
        # Calcular confiança base (score da direção)
        if 'signal_data' in s and isinstance(s['signal_data'], dict):
            sd = s['signal_data']
            if direction == 'COMPRA':
                base_confidence = sd.get('score_buy', 0)
            else:
                base_confidence = sd.get('score_sell', 0)
        else:
            if direction == 'COMPRA':
                base_confidence = s.get('score_buy', 0)
            else:
                base_confidence = s.get('score_sell', 0)
        
        # Aplicar prioridade de contexto (multiplicador)
        priority = get_priority_for_context(
            s.get('market_quality', 0),
            s.get('adx', 0),
            s.get('bollinger_width', 0)
        )
        confidence = base_confidence * priority
        
        # Adicionar pequeno bónus pelo MQ para desempate
        confidence += s.get('market_quality', 0) * 0.05
        
        ranked.append({
            'entry_price': s.get('entry_price'),
            'df': s.get('df'),
            'signal_data': s.get('signal_data'),
            'asset': s.get('asset'),
            'timeframe': s.get('timeframe'),
            'direction': direction,
            'confidence': confidence,
            'score_buy': s.get('score_buy', 0) or (s.get('signal_data', {}).get('score_buy', 0) if 'signal_data' in s else 0),
            'score_sell': s.get('score_sell', 0) or (s.get('signal_data', {}).get('score_sell', 0) if 'signal_data' in s else 0),
            'market_quality': s.get('market_quality', 0),
            'adx': s.get('adx', 0) or (s.get('signal_data', {}).get('adx', 0) if 'signal_data' in s else 0),
            'bollinger_width': s.get('bollinger_width', 0) or (s.get('signal_data', {}).get('bollinger_width', 0) if 'signal_data' in s else 0),
            'reasons_buy': s.get('reasons_buy', []) or (s.get('signal_data', {}).get('reasons_buy', []) if 'signal_data' in s else []),
            'reasons_sell': s.get('reasons_sell', []) or (s.get('signal_data', {}).get('reasons_sell', []) if 'signal_data' in s else []),
            'priority_multiplier': priority
        })
    
    # Ordenar por confiança (decrescente)
    ranked.sort(key=lambda x: x['confidence'], reverse=True)
    
    print(f"[DEBUG] Sinais classificados: {len(ranked)}")
    for r in ranked[:top_n]:
        print(f"[DEBUG] Top: {r['asset']} ({r['direction']}) conf={r['confidence']:.2f}")
    
    return ranked[:top_n]
