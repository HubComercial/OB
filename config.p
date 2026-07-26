import os
from dotenv import load_dotenv

load_dotenv()

from modules.dst_detector import get_portugal_offset
from modules.otc_switcher import should_use_otc, should_use_backtest

# ===== HORÁRIO DE OVERLAY (em UTC) =====
OVERLAY_START = 8    # 8h UTC (9h em Portugal no verão, 8h no inverno)
OVERLAY_END = 18     # 18h UTC (19h em Portugal)

# ===== POLLING ADAPTATIVO =====
POLLING_OVERLAY = 60      # segundos (1 minuto) durante o overlay
POLLING_OFF = 1800        # segundos (30 minutos) fora do overlay

# ===== ANÁLISE DE FIM DE DIA =====
END_OF_DAY_HOUR = 22      # 22h UTC (análise profunda ao final do dia)

# ===== ATIVOS E TIMEFRAMES =====
ASSET = "EURUSD=X"
ASSETS = [
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X",
    "USDCAD=X",
    "NZDUSD=X",
    "EURGBP=X",
    "EURJPY=X",
    "GBPJPY=X",
    "AUDJPY=X"
]
TIMEFRAMES = [1, 5, 15]

OTC_WEEKEND = True
BACKTEST_WEEKEND = True
BACKTEST_CANDLES = 2000

if should_use_otc():
    print("🔄 Modo OTC ativado (fim de semana). Usando ativos OTC.")
    ASSETS = [a.replace("=X", "-OTC") for a in ASSETS]
    ASSET = ASSETS[0]

if should_use_backtest():
    print("🧠 Modo BACKTEST ativado. O robô estudará dados históricos.")

AMOUNT = 1.0
EXPIRY_TIME = 15
TIMEFRAME = 1          # Timeframe base
MIN_INTERVAL = 16

DAILY_LOSS_LIMIT = -10.0
MAX_CONSECUTIVE_LOSSES = 3

# Indicadores
EMA_PERIOD = 10
CCI_PERIOD = 7
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_PERIOD = 14
BB_PERIOD = 20
BB_STD = 2
VOLUME_PERIOD = 20

# Sentimento e volatilidade
SENTIMENT_POSITIVE_THRESHOLD = 0.2
SENTIMENT_NEGATIVE_THRESHOLD = -0.2
SENTIMENT_STRONG_THRESHOLD = 0.6
ATR_PERIOD = 14
ATR_MIN = 0.0005
ATR_MAX = 0.005

ATR_ALERT_THRESHOLD = 0.0003

EMA_50 = 50
EMA_200 = 200
CCI_THRESHOLD = 100

# Credenciais
IQ_EMAIL = os.getenv("IQ_EMAIL")
IQ_PASSWORD = os.getenv("IQ_PASSWORD")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
