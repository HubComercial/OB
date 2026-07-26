def send_telegram_alert(signal, asset, amount, tf, confidence, market_quality, signal_data=None):
    """Envia alerta detalhado ao Telegram com todos os campos do sinal."""
    if notifier is None:
        return

    if signal_data is None:
        signal_data = {}

    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    expiry = CONFIRM_EXPIRY_MAP.get(tf, 2)

    msg = (
        f"🚀 <b>SINAL DE {signal}</b>\n"
        f"📈 Ativo: {asset} ({tf}m)\n"
        f"💰 Valor: ${amount:.2f}\n"
        f"🎯 Confiança: {confidence:.2f}%\n"
        f"📊 Market Quality: {market_quality:.1f}\n"
        f"⏰ Horário: {now} UTC\n"
    )

    if 'score_buy' in signal_data:
        msg += f"🟢 Score Compra: {signal_data['score_buy']:.1f}\n"
    if 'score_sell' in signal_data:
        msg += f"🔴 Score Venda: {signal_data['score_sell']:.1f}\n"
    if 'trend_direction' in signal_data and signal_data['trend_direction']:
        msg += f"📈 Tendência: {signal_data['trend_direction']}\n"
    if 'volume_ratio' in signal_data:
        msg += f"📊 Volume Ratio: {signal_data['volume_ratio']:.2f}\n"
    if 'atr' in signal_data:
        msg += f"📉 ATR: {signal_data['atr']:.5f}\n"
    if 'adx' in signal_data:
        msg += f"📊 ADX: {signal_data['adx']:.1f}\n"
    if 'bollinger_width' in signal_data:
        msg += f"📊 Bollinger Width: {signal_data['bollinger_width']:.4f}\n"

    if signal_data.get('reasons_buy'):
        msg += "\n✅ <b>Razões para COMPRA:</b>\n"
        msg += "\n".join(f"  • {r}" for r in signal_data['reasons_buy'][:5])
    if signal_data.get('reasons_sell'):
        msg += "\n❌ <b>Razões para VENDA:</b>\n"
        msg += "\n".join(f"  • {r}" for r in signal_data['reasons_sell'][:5])

    if signal_data.get('filters_detailed'):
        msg += "\n📋 <b>Filtros:</b>\n"
        for filtro, info in signal_data['filters_detailed'].items():
            status = "✅" if info.get('pass', False) else "❌"
            val = info.get('value', 0)
            min_val = info.get('min', 0)
            msg += f"  {filtro}............. {status} ({val:.3f} ≥ {min_val})\n"

    if signal_data.get('filters_blocked'):
        msg += "\n🚫 <b>Filtros bloqueados:</b>\n"
        msg += "\n".join(f"  • {f}" for f in signal_data['filters_blocked'])

    msg += (
        f"\n💡 <b>Ação:</b> Abra a Pocket Option e execute {signal}.\n"
        f"⏳ Confirmação automática em {expiry} minuto(s)."
    )

    if len(msg) > 4000:
        msg = msg[:3997] + "..."

    notifier.send_message(msg)
