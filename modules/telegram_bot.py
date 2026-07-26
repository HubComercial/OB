import threading
import time
import requests

class TelegramBot:
    def __init__(self, token, chat_id, feedback_recorder):
        self.token = token
        self.chat_id = chat_id
        self.feedback = feedback_recorder
        self.offset = 0
        self.running = True
        self.poll_interval = 5

    def start(self):
        def run():
            while self.running:
                try:
                    self.poll_updates()
                except Exception as e:
                    print(f"⚠️ Erro no polling: {e}")
                time.sleep(self.poll_interval)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def poll_updates(self):
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params = {"offset": self.offset, "timeout": 5}
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return
            data = response.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    self.offset = update["update_id"] + 1
                    self.process_update(update)
        except Exception as e:
            print(f"⚠️ Erro no polling: {e}")

    def process_update(self, update):
        if "message" in update:
            chat_id = update["message"]["chat"]["id"]
            if chat_id != int(self.chat_id):
                return
            text = update["message"].get("text", "")
            if text == "/win":
                self.feedback.confirm_last_signal("WIN")
                self.send_message("✅ Último sinal confirmado como WIN.")
            elif text == "/loss":
                self.feedback.confirm_last_signal("LOSS")
                self.send_message("❌ Último sinal confirmado como LOSS.")
            elif text == "/start":
                self.send_message("🤖 Bot ativo! Use /win ou /loss para confirmar.")

        if text == "/apply_suggestions":
            self.apply_suggestions()
            self.send_message("✅ Sugestões aplicadas com sucesso.")
        elif text == "/reject_suggestions":
            self.reject_suggestions()
            self.send_message("ℹ️ Sugestões rejeitadas. Pode aplicar mais tarde com /apply_suggestions.")


    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"⚠️ Erro ao enviar: {e}")
    def apply_suggestions(self):
        import json, os
        try:
            with open("data/pending_suggestions.json", "r") as f:
                suggestions = json.load(f)
            if not suggestions:
                self.send_message("⚠️ Nenhuma sugestão pendente.")
                return
            with open("config_assets.json", "r") as f:
                config = json.load(f)
            for asset, params in suggestions.items():
                if asset not in config:
                    config[asset] = {}
                for param, data in params.items():
                    config[asset][param] = data["suggested"]
            with open("config_assets.json", "w") as f:
                json.dump(config, f, indent=2)
            os.remove("data/pending_suggestions.json")
            self.send_message("✅ Sugestões aplicadas com sucesso.")
        except Exception as e:
            self.send_message(f"❌ Erro ao aplicar sugestões: {e}")

    def reject_suggestions(self):
        import os
        try:
            os.remove("data/pending_suggestions.json")
            self.send_message("ℹ️ Sugestões rejeitadas.")
        except Exception as e:
            self.send_message(f"❌ Erro ao rejeitar sugestões: {e}")

