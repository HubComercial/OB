import pandas as pd
import json
import os
import copy

try:
    # Caso este ficheiro faça parte do mesmo pacote que signal_generator.py
    from .weights_store import load_weights, save_weights
except ImportError:
    # Caso seja executado como script standalone (ex: cron job de aprendizado)
    from weights_store import load_weights, save_weights

FEEDBACK_FILE = "data/feedback.csv"
STATS_FILE = "data/indicator_stats.json"
CURSOR_FILE = "data/feedback_cursor.json"  # FIX (pt.1): marca até onde já processámos

SMOOTHING_FACTOR = 0.9  # Suavização: 0.9 = muito estável, 0.1 = muito sensível
MIN_SIGNALS_FOR_LEARNING = 20     # mínimo de linhas TOTAIS no csv para começar a aprender
MIN_NEW_CONFIRMED_SIGNALS = 5     # mínimo de novos sinais confirmados desde o último cursor
MIN_SAMPLES_PER_INDICATOR = 5     # mínimo de amostras por indicador (buy/sell separados)

MOTIVE_TO_WEIGHT_BUY = {
    "EMA fast bullish": "ema_fast",
    "EMA trend bullish": "ema_trend",
    "MACD bullish": "macd",
    "CCI positivo": "cci",
    "RSI favorável (tendência)": "rsi",
    "Volume OK": "volume",
    "Bollinger inferior (suporte)": "bollinger",
    "Perto do suporte": "sr",
}

MOTIVE_TO_WEIGHT_SELL = {
    "EMA fast bearish": "ema_fast",
    "EMA trend bearish": "ema_trend",
    "MACD bearish": "macd",
    "CCI negativo": "cci",
    "RSI favorável (tendência baixa)": "rsi",
    "Volume OK": "volume",
    "Bollinger superior (resistência)": "bollinger",
    "Perto da resistência": "sr",
}


def load_stats():
    if os.path.isfile(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            # FIX: except bare escondia qualquer erro; agora só engolimos
            # o que realmente esperamos (ficheiro corrompido/inacessível)
            print("⚠️ indicator_stats.json corrompido. A recomeçar do zero.")
            return {}
    return {}


def save_stats(stats):
    os.makedirs(os.path.dirname(STATS_FILE) or ".", exist_ok=True)
    temp_file = STATS_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(stats, f, indent=2)
    os.replace(temp_file, STATS_FILE)


def _load_cursor():
    """FIX (pt.1 - bug crítico): lê até que linha do feedback.csv já foi
    processada, para não recontar os mesmos trades a cada execução.
    Assume que feedback.csv é append-only (linhas novas só são adicionadas
    ao fim, nunca reordenadas ou apagadas no meio)."""
    if os.path.isfile(CURSOR_FILE):
        try:
            with open(CURSOR_FILE, "r") as f:
                data = json.load(f)
                return int(data.get("last_processed_row", 0))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError):
            print("⚠️ feedback_cursor.json corrompido. A reiniciar do zero (pode gerar recontagem uma única vez).")
    return 0


def _save_cursor(row_count):
    os.makedirs(os.path.dirname(CURSOR_FILE) or ".", exist_ok=True)
    temp_file = CURSOR_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump({"last_processed_row": row_count}, f, indent=2)
    os.replace(temp_file, CURSOR_FILE)


def _is_confirmed(series):
    """FIX (pt.3): comparação robusta contra 'confirmado', que tanto pode
    chegar como bool nativo (pandas costuma inferir True/False do CSV
    automaticamente) como string 'True'/'true'/'1'."""
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "yes"])


def parse_reasons(reasons_str):
    if reasons_str is None:
        return []
    s = str(reasons_str).strip()
    if not s or s in ("[]", "nan", "None"):
        return []
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        pass
    # FIX (pt.8): fallback agora também lida com repr de lista Python
    # (aspas simples, ex: "['EMA fast bullish', 'MACD bullish']"), não só
    # com uma string simples separada por vírgulas.
    cleaned = s.strip('[]')
    parts = [p.strip().strip("'\"") for p in cleaned.split(',')]
    return [p for p in parts if p]


def update_indicator_stats(stats, motives, result, direction):
    """FIX (pt.2 - bug crítico): as estatísticas agora são guardadas
    separadamente por lado ('ema_fast::buy' vs 'ema_fast::sell'). Antes,
    um indicador que funciona bem para VENDA mas mal para COMPRA tinha o
    mesmo accuracy aplicado aos dois pesos, porque as estatísticas de
    ambos os lados eram somadas na mesma chave."""
    mapping = MOTIVE_TO_WEIGHT_BUY if direction == "COMPRA" else MOTIVE_TO_WEIGHT_SELL
    side = "buy" if direction == "COMPRA" else "sell"

    for motive in motives:
        key = mapping.get(motive)
        if key is None:
            continue
        stat_key = f"{key}::{side}"

        if stat_key not in stats:
            stats[stat_key] = {'wins': 0, 'losses': 0, 'total': 0}

        stats[stat_key]['total'] += 1
        if result == "WIN":
            stats[stat_key]['wins'] += 1
        else:
            stats[stat_key]['losses'] += 1


def _weights_changed(old_weights, new_weights, tol=0.01):
    """FIX (pt.5): compara com tolerância em vez de igualdade exata de
    floats, para não gravar uma nova versão por causa de ruído numérico."""
    for side in ('buy', 'sell'):
        old_side = old_weights.get(side, {})
        new_side = new_weights.get(side, {})
        for k, v in new_side.items():
            if abs(v - old_side.get(k, v)) > tol:
                return True
    return False


def optimize_parameters():
    """
    Ajusta os pesos com base nas estatísticas dos indicadores, usando
    suavização exponencial para evitar oscilações.

    FIX (pt.1): processa apenas as linhas NOVAS de feedback.csv desde a
    última execução (via cursor persistido), em vez de reprocessar o
    ficheiro inteiro a cada chamada — o que antes inflava os contadores de
    wins/losses a cada execução repetida.
    """
    try:
        if not os.path.isfile(FEEDBACK_FILE):
            print("📊 feedback.csv não encontrado.")
            return None

        df = pd.read_csv(FEEDBACK_FILE)
        if len(df) < MIN_SIGNALS_FOR_LEARNING:
            print(f"📊 Dados insuficientes para aprendizado (<{MIN_SIGNALS_FOR_LEARNING} registros).")
            return None

        last_processed = _load_cursor()
        if last_processed > len(df):
            # feedback.csv encolheu/foi recriado — cursor não é mais válido
            print("⚠️ feedback.csv tem menos linhas que o cursor guardado. A reiniciar cursor.")
            last_processed = 0

        new_rows = df.iloc[last_processed:]
        if new_rows.empty:
            print("ℹ️ Nenhuma linha nova em feedback.csv desde a última execução.")
            return None

        required_cols = {"confirmado", "resultado", "direcao"}
        if not required_cols.issubset(df.columns):
            print(f"❌ feedback.csv sem colunas obrigatórias: {required_cols - set(df.columns)}")
            return None

        new_conf = new_rows[_is_confirmed(new_rows['confirmado'])]
        if len(new_conf) < MIN_NEW_CONFIRMED_SIGNALS:
            print(f"📊 Poucos sinais novos confirmados ({len(new_conf)}/{MIN_NEW_CONFIRMED_SIGNALS}).")
            # Ainda assim avançamos o cursor: já vimos estas linhas, não
            # queremos reavaliá-las na próxima execução.
            _save_cursor(len(df))
            return None

        wins = new_conf[new_conf['resultado'] == "WIN"]
        losses = new_conf[new_conf['resultado'] == "LOSS"]

        stats = load_stats()

        for _, row in wins.iterrows():
            direction = row.get('direcao')
            if direction not in ("COMPRA", "VENDA"):
                continue
            reasons = parse_reasons(row.get('reasons_buy' if direction == "COMPRA" else 'reasons_sell', '[]'))
            update_indicator_stats(stats, reasons, "WIN", direction)

        for _, row in losses.iterrows():
            direction = row.get('direcao')
            if direction not in ("COMPRA", "VENDA"):
                continue
            reasons = parse_reasons(row.get('reasons_buy' if direction == "COMPRA" else 'reasons_sell', '[]'))
            update_indicator_stats(stats, reasons, "LOSS", direction)

        save_stats(stats)
        _save_cursor(len(df))  # marca estas linhas como já processadas

        weights = load_weights()
        initial_weights = copy.deepcopy(weights)

        for stat_key, data in stats.items():
            if data['total'] < MIN_SAMPLES_PER_INDICATOR:
                continue

            indicator_key, side = stat_key.split("::")
            accuracy = data['wins'] / data['total']
            target_weight = 15 + (accuracy - 0.5) * 20  # 0.5→15, 0.7→19, 0.3→11

            side_weights = weights.get(side)
            if side_weights is None or indicator_key not in side_weights:
                continue

            old_weight = side_weights[indicator_key]
            new_weight = SMOOTHING_FACTOR * old_weight + (1 - SMOOTHING_FACTOR) * target_weight
            side_weights[indicator_key] = max(1, min(25, new_weight))

        if _weights_changed(initial_weights, weights):
            save_weights(weights)
            print(f"📈 Pesos atualizados (versão {weights['version']}):")
            for side in ['buy', 'sell']:
                print(f"  {side}: {weights[side]}")
            return {"weights": weights}
        else:
            print("ℹ️ Nenhuma alteração de pesos significativa.")
            return None

    except Exception as e:
        print(f"❌ Erro no aprendizado: {e}")
        return None
