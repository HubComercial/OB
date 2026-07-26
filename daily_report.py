#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.investigator import generate_report
from modules.notifier import send_telegram_message
import io
import contextlib

def capture_report():
    """Captura a saída do investigador para enviar por Telegram."""
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        generate_report()
    return f.getvalue()

if __name__ == "__main__":
    report = capture_report()
    # Enviar para Telegram (se disponível)
    try:
        send_telegram_message(f"📋 RELATÓRIO DIÁRIO\n\n{report[:4000]}")  # limite do Telegram
    except:
        print(report)
