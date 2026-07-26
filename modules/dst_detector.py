"""
Módulo para detectar automaticamente se Portugal está em horário de verão.
Retorna o offset UTC atual (0 ou +1) e ajusta o overlay.
"""
from datetime import datetime
import zoneinfo

def get_portugal_offset():
    """
    Retorna o offset UTC atual para Portugal (0 ou 1) com base no horário de verão.
    """
    # Define o fuso de Portugal (continente)
    lisbon_tz = zoneinfo.ZoneInfo("Europe/Lisbon")
    now = datetime.now(lisbon_tz)
    # Verifica se está em DST (horário de verão) – offset diferente de 0
    offset_hours = now.utcoffset().total_seconds() / 3600
    return int(offset_hours)

def is_dst():
    """
    Retorna True se Portugal está em horário de verão.
    """
    return get_portugal_offset() == 1
