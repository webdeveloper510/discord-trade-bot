import os
import discord
from trade_executor import get_api
import re
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import discord
from alpaca_trade_api import REST

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Discord Bot logged in as {client.user}")

# ---------------- CONFIG ---------------- #
# SIGNAL_CHANNEL_ID = 1459267180859359357
SIGNAL_CHANNEL_ID = 1463777958010425394

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "pratish@codenomad.net")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD","jldmjuduvlnvbrar")
ALERT_EMAIL_TO = "davinder@codenomad.net"
ALERT_ONLY = True
MAX_RISK_PER_TRADE = 0.20
STOP_LOSS_PERCENT = 0.20
TAKE_PROFIT_PERCENT = 0.20

OPEN_TRADES_FILE = "open_trades.txt"

# ---------------- PERSISTENT TRADES ---------------- #
def load_open_trades():
    if not os.path.exists(OPEN_TRADES_FILE):
        return set()
    with open(OPEN_TRADES_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_open_trade(contract_id):
    with open(OPEN_TRADES_FILE, "a") as f:
        f.write(contract_id + "\n")

OPEN_TRADES = load_open_trades()

# ---------------- EMAIL ---------------- #
def send_trade_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_HOST_USER
    msg["To"] = ALERT_EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    server.send_message(msg)
    server.quit()

# ---------------- ALPACA ---------------- #
def get_api():
    return REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)

# ---------------- PARSING ---------------- #
def parse_bear_contract(text):
    """
    Example signal:
    Contract: SPY 1/19 480C
    """
    pattern = r"Contract:\s*\$?(\w+)\s+(\d{1,2})/(\d{1,2})\s+(\d+)([CP])"
    match = re.search(pattern, text, re.IGNORECASE)

    if not match:
        return None

    symbol, month, day, strike, opt_type = match.groups()

    return {
        "symbol": symbol.upper(),
        "month": int(month),
        "day": int(day),
        "strike": int(strike),
        "type": opt_type.upper(),
    }
    
def build_occ_symbol(contract):
    """
    Converts Bear contract → OCC option symbol
    SPY 1/19 480C → SPY250119C00480000
    """
    year = datetime.now().year % 100
    exp = f"{year:02d}{contract['month']:02d}{contract['day']:02d}"
    strike = f"{contract['strike'] * 1000:08d}"

    return f"{contract['symbol']}{exp}{contract['type']}{strike}"  
  
def extract_entry_price(text):
    patterns = [
        r"Entry:\s*@?\s*(\d+(\.\d+)?)",
        r"@\s*(\d+(\.\d+)?)"
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None

def is_trim_or_update(text):
    keywords = [
        "trim", "trimming", "runner", "update",
        "sold", "sell", "tp", "sl", "stop"
    ]
    return any(k in text.lower() for k in keywords)
# ---------------- POSITION LOGIC ---------------- #
def calculate_position_size(entry_price):
    api = get_api()
    cash = float(api.get_account().cash)
    max_value = cash * MAX_RISK_PER_TRADE

    qty = int(max_value / (entry_price * 100))  # options multiplier
    return max(1, qty)

def place_trade(symbol, qty, entry_price):
    if ALERT_ONLY:
        print(f"ALERT ONLY: {symbol} @ {entry_price} x {qty}")
        return
    api = get_api()

    api.submit_order(
        symbol=symbol,
        qty=qty,
        side="buy",
        type="limit",
        limit_price=entry_price,
        time_in_force="day" 
    )
# ---------------- DISCORD BOT ---------------- #
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id != SIGNAL_CHANNEL_ID:
        return

    text = message.content.strip()

    # Health check
    if text.lower() == "hi":
        await message.channel.send("🤖 Bear Bot is running and listening ✅")
        return

    await message.channel.send("👀 Signal received – checking...")

    # ❌ Ignore trims / updates / sells
    if is_trim_or_update(text):
        await message.channel.send("⛔ Ignored: Trim / update / sell signal")
        return

    # ❌ Require FULL contract
    contract = parse_bear_contract(text)
    if not contract:
        await message.channel.send("⛔ Ignored: No valid contract found")
        return

    occ_symbol = build_occ_symbol(contract)
    contract_id = occ_symbol

    # ❌ Require ENTRY price
    entry_price = extract_entry_price(text)
    if entry_price is None:
        await message.channel.send(
            "⛔ Ignored: No entry price (already in position)"
        )
        return

    # ❌ Prevent duplicate trades
    if contract_id in OPEN_TRADES:
        await message.channel.send("⛔ Ignored: Contract already open")
        return

    try:
        alpaca_symbol = contract_id.split("_")[0]
        qty = calculate_position_size(entry_price)
        place_trade(contract["symbol"], qty, entry_price)

        OPEN_TRADES.add(contract_id)
        save_open_trade(contract_id)

        msg = (
            f"🚀 TRADE EXECUTED\n\n"
            f"Option: {occ_symbol}\n"
            f"Contracts: {qty}\n"
            f"Entry: {entry_price}\n"
            f"Stop: {round(entry_price * (1 - STOP_LOSS_PERCENT), 2)}\n"
            f"Target: {round(entry_price * (1 + TAKE_PROFIT_PERCENT), 2)}\n"
        )

        await message.channel.send(msg)
        send_trade_email("🚨 Bear Bot Trade Executed", msg)

    except Exception as e:
        await message.channel.send(f"❌ Trade Failed: {e}")
        send_trade_email("❌ Bear Bot Trade Failed", str(e))

# ---------------- START ---------------- #
def start_discord():
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    start_discord()

