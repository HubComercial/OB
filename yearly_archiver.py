#!/usr/bin/env python3
"""
yearly_archiver.py – Compacta a pasta de candles do ano para ZIP (nível máximo)
e apaga os CSVs originais para libertar espaço.
Executar automaticamente no final do ano (31 de dezembro) ou manualmente.
"""
import os
import shutil
import zipfile
from datetime import datetime
import sys

def compress_year(year):
    """Compacta a pasta data/candles/{year} para ZIP e apaga os originais."""
    candles_dir = f"data/candles/{year}"
    if not os.path.isdir(candles_dir):
        print(f"⚠️ Pasta {candles_dir} não encontrada. Nada a compactar.")
        return False

    archive_dir = "data/archives"
    os.makedirs(archive_dir, exist_ok=True)
    zip_filename = f"{archive_dir}/{year}.zip"
    zip_filename_temp = zip_filename + ".tmp"

    print(f"📦 A compactar {candles_dir} → {zip_filename}...")

    total_files = 0
    try:
        with zipfile.ZipFile(zip_filename_temp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, dirs, files in os.walk(candles_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, candles_dir)
                    zipf.write(file_path, arcname)
                    total_files += 1
                    # Progresso a cada 10 ficheiros
                    if total_files % 10 == 0:
                        print(f"  {total_files} ficheiros compactados...")

        # Substituir o ficheiro temporário pelo definitivo
        os.replace(zip_filename_temp, zip_filename)

        # Apagar a pasta original após compactação bem-sucedida
        shutil.rmtree(candles_dir)
        print(f"✅ Compactação concluída: {total_files} ficheiros → {zip_filename} (tamanho: {os.path.getsize(zip_filename) / (1024**3):.2f} GB)")
        print(f"🗑️  Pasta {candles_dir} removida.")
        return True

    except Exception as e:
        print(f"❌ Erro durante a compactação: {e}")
        # Tentar apagar o ficheiro temporário, se existir
        if os.path.exists(zip_filename_temp):
            os.remove(zip_filename_temp)
        return False

def main():
    now = datetime.now()
    year = str(now.year - 1)  # Compactar o ano anterior (já completo)

    # Se houver argumento, usar o ano especificado
    if len(sys.argv) > 1:
        year = sys.argv[1]

    print(f"📅 A compactar dados do ano {year}...")
    compress_year(year)

if __name__ == "__main__":
    main()
