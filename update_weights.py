#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.dynamic_scorer import get_weight_recommendations, apply_weights_suggestion

if __name__ == "__main__":
    print("📊 Analisando dados para recomendação de pesos...")
    suggestions = get_weight_recommendations()
    if suggestions:
        print("\n📌 Sugestão de novos pesos:")
        for k, v in suggestions.items():
            print(f"  {k}: {v:.2f}")
        print("\n⚠️ Para aplicar estas sugestões, edite data/weights.json manualmente.")
        print("   Ou execute: python update_weights.py --apply")
    else:
        print("⚠️ Dados insuficientes (mínimo 10 trades confirmados).")
