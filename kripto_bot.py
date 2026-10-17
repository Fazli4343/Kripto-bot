import asyncio
import os
import re

import ccxt.async_support as ccxt
from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

EXCHANGES = ["binance", "coinbase", "kraken", "okx", "bybit",
             "kucoin", "gateio", "bitget", "mexc", "btcturk"]

ALIASES = {
    "ether": "ETH", "ethereum": "ETH", "eth": "ETH",
    "bitcoin": "BTC", "btc": "BTC",
    "solana": "SOL", "sol": "SOL",
    "xrp": "XRP", "ripple": "XRP",
    "bnb": "BNB", "doge": "DOGE", "dogecoin": "DOGE",
    "avax": "AVAX", "avalanche": "AVAX",
    "ada": "ADA", "cardano": "ADA",
    "link": "LINK", "chainlink": "LINK",
    "ton": "TON", "trx": "TRX", "tron": "TRX",
    "matic": "POL", "pol": "POL", "shib": "SHIB",
    "ltc": "LTC", "litecoin": "LTC", "dot": "DOT", "polkadot": "DOT",
}


def find_coin(text: str):
    words = re.findall(r"[a-zA-Z]+", text.lower())
    for w in words:
        if w in ALIASES:
            return ALIASES[w]
    return words[-1].upper() if words else None


async def fetch_one(name: str, coin: str):
    ex = getattr(ccxt, name)({"enableRateLimit": True, "timeout": 8000})
    try:
        for quote in ("USDT", "USD"):
            try:
                t = await ex.fetch_ticker(f"{coin}/{quote}")
                if t.get("ask"):
                    return {"ex": name, "quote": quote,
                            "ask": t["ask"], "bid": t.get("bid")}
            except Exception:
                continue
    finally:
        await ex.close()
    return None


async def compare(coin: str) -> str:
    results = await asyncio.gather(*(fetch_one(e, coin) for e in EXCHANGES))
    rows = sorted([r for r in results if r], key=lambda r: r["ask"])
    if not rows:
        return f"{coin} için hiçbir borsada fiyat bulamadım."

    best, worst = rows[0], rows[-1]
    lines = [f"💰 {coin} — en ucuzdan pahalıya (alış fiyatı)\n"]
    for i, r in enumerate(rows):
        mark = "🥇" if i == 0 else "  "
        lines.append(f"{mark} {r['ex'].capitalize():<9} {r['ask']:,.4f} {r['quote']}")
    diff = (worst["ask"] - best["ask"]) / best["ask"] * 100
    lines.append(f"\n✅ En ucuz: {best['ex'].capitalize()}")
    lines.append(f"📊 En ucuz ile en pahalı arası fark: %{diff:.2f}")
    lines.append("\n⚠️ Komisyon, transfer ücreti ve USD/USDT farkı dahil değil.")
    return "\n".join(lines)


async def handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if ctx.args:
        text = " ".join(ctx.args)
    coin = find_coin(text)
    if not coin:
        await update.message.reply_text("Hangi kripto? Örn: ether nerede ucuz")
        return
    msg = await update.message.reply_text(f"{coin} fiyatları çekiliyor…")
    await msg.edit_text(await compare(coin))


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! Bir kripto adı yaz, borsaları karşılaştırayım.\n"
        "Örnek: ether nerede ucuz | btc | /fiyat sol")


def main():
    app = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["fiyat", "price"], handle))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()


if __name__ == "__main__":
    main()
