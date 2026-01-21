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
# DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
# ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
# ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

# EMAIL_HOST = "smtp.gmail.com"
# EMAIL_PORT = 587
# EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "pratish@codenomad.net")
# EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "jldmjuduvlnvbrar")
# ALERT_EMAIL_TO = "davinder@codenomad.net"


# ---------------- CONFIG ---------------- #

SIGNAL_CHANNEL_ID = 1459267180859359357
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "pratish@codenomad.net")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
ALERT_EMAIL_TO = "davinder@codenomad.net"

MAX_RISK_PER_TRADE = 0.20      # 20%
STOP_LOSS_PERCENT = 0.20       # 20%
PRICE_TOLERANCE = 0.03         # 3% slippage allowed


OPEN_TRADES = set()

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
    pattern = r"Contract:\s*\$?(\w+)\s+(\d{1,2}/\d{1,2})\s+(\d+)([CP])"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None

    symbol, exp, strike, opt_type = match.groups()
    year = datetime.now().year
    month, day = exp.split("/")

    return {
        "symbol": symbol.upper(),
        "expiry": f"{year}-{month.zfill(2)}-{day.zfill(2)}",
        "strike": strike,
        "type": "CALL" if opt_type.upper() == "C" else "PUT"
    }

def extract_entry_price(text):
    patterns = [
        r"Entry:\s*@\s*(\d+(\.\d+)?)",
        r"Entry\s*@\s*(\d+(\.\d+)?)",
        r"@\s*(\d+(\.\d+)?)"
    ]

    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None

def is_trim_or_update(text):
    t = text.lower()
    keywords = [
        "trim",
        "trimming",
        "runner",
        "update",
        "updates",
        "up ",
        "setting my sl",
        "sl to be",
        "stop loss",
        "notes:",
        "this is the setup"
    ]
    return any(k in t for k in keywords)

# ---------------- SMART LOGIC ---------------- #

def is_price_close_to_entry(symbol, entry_price):
    api = get_api()
    last_price = api.get_last_trade(symbol).price
    tolerance = entry_price * PRICE_TOLERANCE
    return abs(last_price - entry_price) <= tolerance

def calculate_position_size(entry_price):
    api = get_api()
    account = api.get_account()
    cash = float(account.cash)

    max_value = cash * MAX_RISK_PER_TRADE
    qty = int(max_value / entry_price)

    return max(1, qty)

def place_trade(symbol, qty, entry_price):
    api = get_api()
    stop_price = round(entry_price * (1 - STOP_LOSS_PERCENT), 2)

    api.submit_order(
        symbol=symbol,
        qty=qty,
        side="buy",
        type="market",
        time_in_force="day",
        order_class="bracket",
        stop_loss={"stop_price": stop_price}
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

    text = message.content

    # Ignore trims / updates / management
    if is_trim_or_update(text):
        return

    contract = parse_bear_contract(text)
    if not contract:
        return

    entry_price = extract_entry_price(text)
    if entry_price is None:
        return  # No entry = already in trade

    symbol = contract["symbol"]

    if symbol in OPEN_TRADES:
        return

    if not is_price_close_to_entry(symbol, entry_price):
        return

    try:
        qty = calculate_position_size(entry_price)
        place_trade(symbol, qty, entry_price)

        OPEN_TRADES.add(symbol)

        msg = (
            f"🚀 NEW TRADE EXECUTED\n\n"
            f"Symbol: {symbol}\n"
            f"Contracts: {qty}\n"
            f"Entry: {entry_price}\n"
            f"Stop Loss: {round(entry_price * (1 - STOP_LOSS_PERCENT), 2)}\n"
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
    
    


# # ---------------- EMAIL ---------------- #

# def send_trade_email(subject, body):
#     msg = MIMEMultipart()
#     msg["From"] = EMAIL_HOST_USER
#     msg["To"] = ALERT_EMAIL_TO
#     msg["Subject"] = subject
#     msg.attach(MIMEText(body, "plain"))

#     server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
#     server.starttls()
#     server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
#     server.send_message(msg)
#     server.quit()

# # ---------------- ALPACA ---------------- #

# def get_api():
#     return REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)

# # ---------------- SIGNAL PARSER ---------------- #

# def parse_bear_signal(text):
#     pattern = r"Contract:\s*(\w+)\s+(\d{1,2}/\d{1,2})\s+(\d+)([CP])"
#     match = re.search(pattern, text)

#     if not match:
#         return None

#     symbol, exp, strike, opt_type = match.groups()
#     year = datetime.now().year
#     month, day = exp.split("/")

#     return {
#         "symbol": symbol,
#         "expiry": f"{year}-{month.zfill(2)}-{day.zfill(2)}",
#         "strike": strike,
#         "type": "call" if opt_type == "C" else "put"
#     }

# # ---------------- SMART LOGIC ---------------- #

# def is_trim_message(text):
#     return "trim" in text.lower() or "scalp" in text.lower()

# def calculate_position_size(symbol, entry_price):
#     api = get_api()
#     account = api.get_account()
#     cash = float(account.cash)
#     max_trade_value = cash * MAX_RISK_PER_TRADE
#     qty = int(max_trade_value / entry_price)
#     return max(1, qty)

# def is_price_in_range(symbol, expected_price):
#     api = get_api()
#     last = api.get_last_trade(symbol).price
#     lower = expected_price * (1 - PRICE_TOLERANCE)
#     upper = expected_price * (1 + PRICE_TOLERANCE)
#     return lower <= last <= upper

# def place_trade_with_stop(symbol, qty, entry_price):
#     api = get_api()
#     stop_price = round(entry_price * (1 - STOP_LOSS_PERCENT), 2)

#     return api.submit_order(
#         symbol=symbol,
#         qty=qty,
#         side="buy",
#         type="market",
#         time_in_force="day",
#         order_class="bracket",
#         stop_loss={"stop_price": stop_price}
#     )

# # ---------------- DISCORD BOT ---------------- #

# intents = discord.Intents.default()
# intents.message_content = True
# client = discord.Client(intents=intents)

# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return
#     if message.channel.id != SIGNAL_CHANNEL_ID:
#         return
#     if is_trim_message(message.content):
#         return
#     signal = parse_bear_signal(message.content)
#     if not signal:
#         return

#     try:
#         api = get_api()
#         expected_price = api.get_last_trade(signal["symbol"]).price
#         if not is_price_in_range(signal["symbol"], expected_price):
#             return
#         entry_price = expected_price
#         qty = calculate_position_size(signal["symbol"], entry_price)
#         place_trade_with_stop(signal["symbol"], qty, entry_price)
#         trade_msg = (
#             f"🚀 Trade Executed Successfully\n\n"
#             f"Symbol: {signal['symbol']}\n"
#             f"Qty: {qty}\n"
#             f"Entry: {entry_price}\n"
#             f"Stop Loss: {round(entry_price * (1 - STOP_LOSS_PERCENT), 2)}\n"
#         )

#         await message.channel.send(trade_msg)
#         send_trade_email("🚨 Smart Trading Bot – Trade Executed", trade_msg)

#     except Exception as e:
#         await message.channel.send(f"❌ Trade Failed: {e}")
#         send_trade_email("❌ Smart Trading Bot – Trade Failed", str(e))

# # ---------------- START ---------------- #

# def start_discord():
#     client.run(DISCORD_TOKEN)

# if __name__ == "__main__":
#     start_discord()

