"""
modules/telemetry.py
Sistema de telemetria para monitorizar o comportamento do robô.
"""
import json
import os
from datetime import datetime, timezone
from collections import defaultdict

TELEMETRY_FILE = "data/telemetry_daily.json"

class Telemetry:
    def __init__(self):
        self.reset_cycle()
        self.daily_data = self._load_daily()

    def reset_cycle(self):
        self.cycle_data = {
            'ativos_analisados': 0,
            'rejeicoes': defaultdict(int),  # {'MQ': 0, 'ADX': 0, 'BW': 0, 'Score': 0, 'DadosInsuf': 0}
            'ranking': 0,
            'executado': 0,
            'executado_asset': None,
            'tempo_total': 0.0,
            'tempos_por_ativo': [],
            'reconexoes': 0,
            'erros': 0
        }

    def _load_daily(self):
        if os.path.isfile(TELEMETRY_FILE):
            try:
                with open(TELEMETRY_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_daily(self):
        with open(TELEMETRY_FILE, 'w') as f:
            json.dump(self.daily_data, f, indent=2)

    def add_asset_analysis(self, asset, motivo=None):
        self.cycle_data['ativos_analisados'] += 1
        if motivo:
            self.cycle_data['rejeicoes'][motivo] += 1

    def add_ranking(self):
        self.cycle_data['ranking'] += 1

    def add_executed(self, asset):
        self.cycle_data['executado'] += 1
        self.cycle_data['executado_asset'] = asset

    def add_reconexao(self):
        self.cycle_data['reconexoes'] += 1

    def add_erro(self):
        self.cycle_data['erros'] += 1

    def add_tempo_ativo(self, tempo):
        self.cycle_data['tempos_por_ativo'].append(tempo)

    def set_tempo_total(self, tempo):
        self.cycle_data['tempo_total'] = tempo

    def get_cycle_summary(self):
        data = self.cycle_data
        total_rejeicoes = sum(data['rejeicoes'].values())
        return {
            'ativos_analisados': data['ativos_analisados'],
            'rejeicoes': dict(data['rejeicoes']),
            'total_rejeicoes': total_rejeicoes,
            'ranking': data['ranking'],
            'executado': data['executado'],
            'executado_asset': data['executado_asset'],
            'tempo_total': round(data['tempo_total'], 1),
            'tempo_medio': round(sum(data['tempos_por_ativo']) / len(data['tempos_por_ativo']), 1) if data['tempos_por_ativo'] else 0,
            'reconexoes': data['reconexoes'],
            'erros': data['erros']
        }

    def print_cycle_summary(self):
        s = self.get_cycle_summary()
        print("\n" + "=" * 50)
        print("📊 RESUMO DO CICLO")
        print("=" * 50)
        print(f"Ativos analisados: {s['ativos_analisados']}")
        print("❌ Rejeitados:")
        if s['rejeicoes']:
            for motivo, count in s['rejeicoes'].items():
                print(f"   {motivo}.............{count}")
        else:
            print("   Nenhum")
        print(f"✅ Ranking: {s['ranking']}")
        print(f"🚀 Executado: {s['executado']} ({s['executado_asset'] or 'Nenhum'})")
        print(f"⏱ Tempo total: {s['tempo_total']}s")
        print(f"⏱ Tempo médio por ativo: {s['tempo_medio']}s")
        print(f"🔄 Reconexões: {s['reconexoes']}")
        print(f"❌ Erros: {s['erros']}")
        print("=" * 50 + "\n")

    def update_daily(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today not in self.daily_data:
            self.daily_data[today] = {
                'ativos_analisados': 0,
                'rejeicoes': defaultdict(int),
                'ranking': 0,
                'executado': 0,
                'reconexoes': 0,
                'erros': 0,
                'ciclos': 0
            }
        daily = self.daily_data[today]

        if not isinstance(daily.get('rejeicoes'), defaultdict):
            daily['rejeicoes'] = defaultdict(int, daily.get('rejeicoes', {}))

        daily['ativos_analisados'] += self.cycle_data['ativos_analisados']
        for k, v in self.cycle_data['rejeicoes'].items():
            if k not in daily['rejeicoes']:
                daily['rejeicoes'][k] = 0
            daily['rejeicoes'][k] += v
        daily['ranking'] += self.cycle_data['ranking']
        daily['executado'] += self.cycle_data['executado']
        daily['reconexoes'] += self.cycle_data['reconexoes']
        daily['erros'] += self.cycle_data['erros']
        daily['ciclos'] += 1
        self._save_daily()

    def get_daily_summary(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily = self.daily_data.get(today, {})
        if not daily:
            return "📊 Nenhum dado para hoje."
        total = daily.get('ativos_analisados', 0)
        rejeicoes = daily.get('rejeicoes', {})
        ranking = daily.get('ranking', 0)
        executado = daily.get('executado', 0)
        reconexoes = daily.get('reconexoes', 0)
        erros = daily.get('erros', 0)
        ciclos = daily.get('ciclos', 0)
        msg = f"📊 <b>RESUMO DO DIA ({today})</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"Ativos analisados: {total}\n"
        for motivo, count in rejeicoes.items():
            pct = (count / total * 100) if total > 0 else 0
            msg += f"{motivo}.............{count} ({pct:.0f}%)\n"
        msg += f"✅ Ranking: {ranking}\n"
        msg += f"🚀 Executado: {executado}\n"
        msg += f"🔄 Reconexões: {reconexoes}\n"
        msg += f"❌ Erros: {erros}\n"
        msg += f"📦 Ciclos: {ciclos}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━"
        return msg

    def send_daily_report(self, notifier):
        msg = self.get_daily_summary()
        if notifier:
            notifier.send_message(msg)
