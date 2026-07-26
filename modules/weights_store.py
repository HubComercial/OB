"""Módulo único para leitura/escrita de data/weights.json.

Antes, `signal_generator.py` e o learner (`optimize_parameters`) tinham cada
um a sua própria versão de load_weights()/save_weights(), com regras de
cache e defaults ligeiramente diferentes. Isso é um risco: se um dia só um
dos dois for corrigido, os dois módulos passam a discordar sobre os pesos
"atuais". Este módulo é a única fonte de verdade para ambos.
"""
import os
import json
import copy
import hashlib
import datetime

WEIGHTS_FILE = "data/weights.json"

_weights_cache = None
_weights_hash = None
_weights_mtime = None


def _get_file_hash(filepath):
    if not os.path.isfile(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def load_weights():
    """Carrega pesos com cache em duas camadas (mtime barato, hash como
    confirmação) e fallback para pesos padrão via deepcopy."""
    global _weights_cache, _weights_hash, _weights_mtime

    try:
        current_mtime = os.stat(WEIGHTS_FILE).st_mtime
    except OSError:
        current_mtime = None

    if _weights_cache is not None and current_mtime is not None and current_mtime == _weights_mtime:
        return _weights_cache

    current_hash = _get_file_hash(WEIGHTS_FILE) if current_mtime is not None else None

    if _weights_cache is not None and current_hash is not None and _weights_hash == current_hash:
        _weights_mtime = current_mtime
        return _weights_cache

    try:
        if os.path.isfile(WEIGHTS_FILE):
            with open(WEIGHTS_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'buy' in data and 'sell' in data:
                    _weights_cache = data
                    _weights_hash = current_hash
                    _weights_mtime = current_mtime
                    return _weights_cache
    except (json.JSONDecodeError, KeyError, TypeError):
        print("⚠️ weights.json corrompido ou inválido. Usando pesos padrão.")

    from config import SCORE_WEIGHTS  # import tardio para evitar import circular
    default_weights = {
        'version': 1,
        'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'buy': copy.deepcopy(SCORE_WEIGHTS),
        'sell': copy.deepcopy(SCORE_WEIGHTS)
    }
    _weights_cache = default_weights
    _weights_hash = current_hash
    _weights_mtime = current_mtime
    return _weights_cache


def save_weights(weights):
    """Grava pesos de forma atómica (ficheiro temporário + rename) e
    invalida o cache em memória para que a próxima load_weights() releia."""
    global _weights_cache, _weights_hash, _weights_mtime

    weights['version'] = weights.get('version', 0) + 1
    weights['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    os.makedirs(os.path.dirname(WEIGHTS_FILE) or ".", exist_ok=True)
    temp_file = WEIGHTS_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(weights, f, indent=2)
    os.replace(temp_file, WEIGHTS_FILE)

    # FIX: sem isto, um processo de longa duração que chama save_weights()
    # e depois load_weights() no mesmo segundo podia continuar a ver o
    # valor antigo em cache (mtime com resolução de 1s em alguns sistemas).
    _weights_cache = None
    _weights_hash = None
    _weights_mtime = None
