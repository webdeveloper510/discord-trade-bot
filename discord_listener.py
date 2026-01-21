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
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD","jldmjuduvlnvbrar")
ALERT_EMAIL_TO = "davinder@codenomad.net"

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
# def parse_bear_contract(text):
#     """
#     Extract FULL option contract (symbol + exp + strike + type)
#     """
#     pattern = r"Contract:\s*\$?(\w+)\s+(\d{1,2}/\d{1,2})\s+(\d+)([CP])"
#     match = re.search(pattern, text, re.IGNORECASE)
#     if not match:
#         return None

#     symbol, exp, strike, opt_type = match.groups()
#     return f"{symbol.upper()}_{exp}_{strike}{opt_type.upper()}"
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

# def is_trim_or_update(text):
#     keywords = [
#         "trim", "trimming", "runner", "update",
#         "stop", "sl", "tp", "sold", "sell"
#     ]
#     return any(k in text.lower() for k in keywords)

def is_trim_or_update(text):
    keywords = [
        "trim", "trimming", "runner", "update",
        "sold", "sell", "tp", "sl", "stop"
    ]
    return any(k in text.lower() for k in keywords)
# ---------------- POSITION LOGIC ---------------- #
# def calculate_position_size(entry_price):
#     api = get_api()
#     cash = float(api.get_account().cash)
#     max_value = cash * MAX_RISK_PER_TRADE
#     qty = int(max_value / entry_price)
#     return max(1, qty)
def calculate_position_size(entry_price):
    api = get_api()
    cash = float(api.get_account().cash)
    max_value = cash * MAX_RISK_PER_TRADE

    qty = int(max_value / (entry_price * 100))  # options multiplier
    return max(1, qty)

def place_trade(symbol, qty, entry_price):
    api = get_api()

    stop_price = round(entry_price * (1 - STOP_LOSS_PERCENT), 2)
    if stop_price >= entry_price:
        stop_price = round(entry_price - 0.01, 2)

    take_profit_price = max(
        round(entry_price * (1 + TAKE_PROFIT_PERCENT), 2),
        round(entry_price + 0.01, 2)
    )

    api.submit_order(
        symbol=symbol,
        qty=qty,
        side="buy",
        type="limit",
        limit_price=entry_price,
        time_in_force="day",
        order_class="bracket",
        stop_loss={"stop_price": stop_price},
        take_profit={"limit_price": take_profit_price},
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
    # contract_id = parse_bear_contract(text)
    # if not contract_id:
    #     await message.channel.send("⛔ Ignored: No contract found")
    #     return

    # ❌ Require ENTRY price
    entry_price = extract_entry_price(text)
    if entry_price is None:
        await message.channel.send(
            "⛔ Ignored: No entry price (already in position)"
        )
        return
    # entry_price = extract_entry_price(text)
    # if entry_price is None:
    #     await message.channel.send("⛔ Ignored: No entry price (already bought)")
    #     return

    # ❌ Prevent duplicate trades
    if contract_id in OPEN_TRADES:
        await message.channel.send("⛔ Ignored: Contract already open")
        return

    try:
        alpaca_symbol = contract_id.split("_")[0]
        qty = calculate_position_size(entry_price)
        place_trade(occ_symbol, qty, entry_price)

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




# MAX_RISK_PER_TRADE = 0.20      # 20%
# STOP_LOSS_PERCENT = 0.20       # 20%
# PRICE_TOLERANCE = 0.10  # 10% tolerance
# TAKE_PROFIT_PERCENT = 0.20  # 20% target
# STOP_LOSS_PERCENT = 0.20 

# OPEN_TRADES_FILE = "open_trades.txt"
# # ---------------- PERSISTENT TRADES ---------------- #
# def load_open_trades():
#     if not os.path.exists(OPEN_TRADES_FILE):
#         return set()
#     with open(OPEN_TRADES_FILE, "r") as f:
#         return set(line.strip() for line in f)

# def save_open_trade(symbol):
#     with open(OPEN_TRADES_FILE, "a") as f:
#         f.write(symbol + "\n")

# OPEN_TRADES = load_open_trades()

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

# # ---------------- PARSING ---------------- #
# def parse_bear_contract(text):
#     pattern = r"Contract:\s*\$?(\w+)\s+(\d{1,2}/\d{1,2})\s+(\d+)([CP])"
#     match = re.search(pattern, text, re.IGNORECASE)
#     if not match:
#         return None
#     symbol, exp, strike, opt_type = match.groups()
#     return symbol.upper()

# def extract_entry_price(text):
#     patterns = [
#         r"Entry:\s*@?\s*(\d+(\.\d+)?)",
#         r"@\s*(\d+(\.\d+)?)"
#     ]
#     for p in patterns:
#         match = re.search(p, text, re.IGNORECASE)
#         if match:
#             return float(match.group(1))
#     return None

# def is_trim_or_update(text):
#     keywords = ["trim", "trimming", "runner", "update", "stop", "sl", "tp", "sold", "sell"]
#     t = text.lower()
#     return any(k in t for k in keywords)

# # ---------------- SMART LOGIC ---------------- #
# def is_price_close_to_entry(entry_price, market_price=None):
#     """
#     Always True for options (no Alpaca bars). 
#     Optional market_price can be used if available.
#     """
#     if market_price is None:
#         # Skip check for options
#         print(f"[DEBUG] Skipping price check for entry price {entry_price}")
#         return True

#     tolerance = max(entry_price * PRICE_TOLERANCE, 0.01)
#     lower_bound = entry_price - tolerance
#     upper_bound = entry_price + tolerance
#     can_trade = lower_bound <= market_price <= upper_bound

#     print(f"[DEBUG] Entry: {entry_price}, Market: {market_price}, "
#           f"Allowed: ({lower_bound:.2f}-{upper_bound:.2f}), Can trade? {can_trade}")
#     return can_trade

# def calculate_position_size(entry_price):
#     api = get_api()
#     cash = float(api.get_account().cash)
#     max_value = cash * MAX_RISK_PER_TRADE
#     qty = int(max_value / entry_price)
#     return max(1, qty)

# def place_trade(symbol, qty, entry_price):
#     api = get_api()

#     # -------- STOP LOSS -------- #
#     stop_price = entry_price * (1 - STOP_LOSS_PERCENT)

#     # Ensure stop < entry
#     if stop_price >= entry_price:
#         stop_price = entry_price - 0.01

#     # Options → always 2 decimals
#     stop_price = round(stop_price, 2)
#     # -------- TAKE PROFIT -------- #
#     # 1) Calculate % target
#     tp_percent_price = entry_price * (1 + TAKE_PROFIT_PERCENT)
#     # 2) FORCE Alpaca rule: tp >= entry + 0.01
#     min_tp_price = entry_price + 0.01
#     # 3) Pick the higher one
#     take_profit_price = max(tp_percent_price, min_tp_price)
#     # 4) ROUND AFTER choosing (IMPORTANT)
#     take_profit_price = round(take_profit_price, 2)
#     # 5) FINAL SAFETY CHECK (this is the key fix)
#     if take_profit_price < round(entry_price + 0.01, 2):
#         take_profit_price = round(entry_price + 0.01, 2)

#     print(
#         f"[DEBUG] Entry={entry_price} | "
#         f"Stop={stop_price} | "
#         f"TakeProfit={take_profit_price}"
#     )

#     api.submit_order(
#     symbol=symbol,
#     qty=qty,
#     side="buy",
#     type="limit",                 # ✅ REQUIRED
#     limit_price=entry_price,      # ✅ REQUIRED
#     time_in_force="day",
#     order_class="bracket",
#     stop_loss={"stop_price": stop_price},
#     take_profit={"limit_price": take_profit_price}
# )
#     print(f"[DEBUG] Trade executed ✅ {symbol}")
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

#     text = message.content.strip()

#     # Health check
#     if text.lower() == "hi":
#         await message.channel.send("🤖 Bear Bot is running and listening ✅")
#         return

#     await message.channel.send("👀 Signal received – checking...")

#     if is_trim_or_update(text):
#         await message.channel.send("⛔ Ignored: Trim / update message")
#         return

#     symbol = parse_bear_contract(text)
#     if not symbol:
#         await message.channel.send("⛔ Ignored: No contract found")
#         return

#     entry_price = extract_entry_price(text)
#     if entry_price is None:
#         await message.channel.send("⛔ Ignored: No entry price")
#         return

#     if symbol in OPEN_TRADES:
#         await message.channel.send("⛔ Ignored: Trade already open")
#         return

#     # Skip price check for options
#     if not is_price_close_to_entry(entry_price):
#         await message.channel.send("⛔ Ignored: Price moved too far")
#         return

#     try:
#         qty = calculate_position_size(entry_price)
#         place_trade(symbol, qty, entry_price)
#         OPEN_TRADES.add(symbol)
#         save_open_trade(symbol)
#         stop_price = round(entry_price * (1 - STOP_LOSS_PERCENT), 2)

#         msg = (
#             f"🚀 TRADE EXECUTED\n\n"
#             f"Symbol: {symbol}\n"
#             f"Contracts: {qty}\n"
#             f"Entry: {entry_price}\n"
#             f"Stop Loss: {stop_price}\n"
#         )

#         # Debug info in Discord
#         await message.channel.send(
#             f"🤖 Debug Info:\n"
#             f"Symbol: {symbol}\n"
#             f"Entry Price: {entry_price}\n"
#             f"Qty: {qty}\n"
#             f"Stop Loss: {stop_price}\n"
#             f"Price check skipped ✅"
#         )

#         await message.channel.send(msg)
#         send_trade_email("🚨 Bear Bot Trade Executed", msg)

#     except Exception as e:
#         await message.channel.send(f"❌ Trade Failed: {e}")
#         send_trade_email("❌ Bear Bot Trade Failed", str(e))

# # ---------------- START ---------------- #
# def start_discord():
#     client.run(DISCORD_TOKEN)

# if __name__ == "__main__":
#     start_discord()











































# OPEN_TRADES = set()

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

# # ---------------- PARSING ---------------- #

# def parse_bear_contract(text):
#     pattern = r"Contract:\s*\$?(\w+)\s+(\d{1,2}/\d{1,2})\s+(\d+)([CP])"
#     match = re.search(pattern, text, re.IGNORECASE)
#     if not match:
#         return None

#     symbol, exp, strike, opt_type = match.groups()
#     year = datetime.now().year
#     month, day = exp.split("/")

#     return {
#         "symbol": symbol.upper(),
#         "expiry": f"{year}-{month.zfill(2)}-{day.zfill(2)}",
#         "strike": strike,
#         "type": "CALL" if opt_type.upper() == "C" else "PUT"
#     }

# def extract_entry_price(text):
#     patterns = [
#         r"Entry:\s*@\s*(\d+(\.\d+)?)",
#         r"Entry\s*@\s*(\d+(\.\d+)?)",
#         r"@\s*(\d+(\.\d+)?)"
#     ]

#     for p in patterns:
#         match = re.search(p, text, re.IGNORECASE)
#         if match:
#             return float(match.group(1))

#     return None

# def is_trim_or_update(text):
#     t = text.lower()
#     keywords = [
#         "trim",
#         "trimming",
#         "runner",
#         "update",
#         "updates",
#         "up ",
#         "setting my sl",
#         "sl to be",
#         "stop loss",
#         "notes:",
#         "this is the setup"
#     ]
#     return any(k in t for k in keywords)

# # ---------------- SMART LOGIC ---------------- #

# def is_price_close_to_entry(symbol, entry_price):
#     api = get_api()
#     last_price = api.get_last_trade(symbol).price
#     tolerance = entry_price * PRICE_TOLERANCE
#     return abs(last_price - entry_price) <= tolerance

# def calculate_position_size(entry_price):
#     api = get_api()
#     account = api.get_account()
#     cash = float(account.cash)

#     max_value = cash * MAX_RISK_PER_TRADE
#     qty = int(max_value / entry_price)

#     return max(1, qty)

# def place_trade(symbol, qty, entry_price):
#     api = get_api()
#     stop_price = round(entry_price * (1 - STOP_LOSS_PERCENT), 2)

#     api.submit_order(
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

#     text = message.content.strip().lower()

#     # ---------------- HEALTH CHECK ---------------- #
#     if text == "hi":
#         await message.channel.send("🤖 Bear Bot is running and listening ✅")
#         return

#     # ACK every message so you know bot is alive
#     await message.channel.send("👀 Signal received – checking...")

#     original_text = message.content

#     # Ignore trims / updates / management
#     if is_trim_or_update(original_text):
#         await message.channel.send("⛔ Ignored: Trim / update / management message")
#         return

#     contract = parse_bear_contract(original_text)
#     if not contract:
#         await message.channel.send("⛔ Ignored: No valid contract found")
#         return

#     entry_price = extract_entry_price(original_text)
#     if entry_price is None:
#         await message.channel.send(
#             "⛔ Ignored: No entry price found\n"
#             "ℹ️ This usually means the trade was already entered earlier."
#         )
#         return

#     symbol = contract["symbol"]

#     if symbol in OPEN_TRADES:
#         await message.channel.send("⛔ Ignored: Trade already open for this symbol")
#         return

#     if not is_price_close_to_entry(symbol, entry_price):
#         await message.channel.send(
#             "⛔ Ignored: Current price too far from entry"
#         )
#         return

#     try:
#         qty = calculate_position_size(entry_price)
#         place_trade(symbol, qty, entry_price)

#         OPEN_TRADES.add(symbol)

#         stop_price = round(entry_price * (1 - STOP_LOSS_PERCENT), 2)

#         msg = (
#             f"🚀 NEW TRADE EXECUTED\n\n"
#             f"Symbol: {symbol}\n"
#             f"Contracts: {qty}\n"
#             f"Entry: {entry_price}\n"
#             f"Stop Loss: {stop_price}\n"
#         )

#         await message.channel.send(msg)
#         send_trade_email("🚨 Bear Bot Trade Executed", msg)

#     except Exception as e:
#         await message.channel.send(f"❌ Trade Failed: {e}")
#         send_trade_email("❌ Bear Bot Trade Failed", str(e))
        
        
# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return

#     if message.channel.id != SIGNAL_CHANNEL_ID:
#         return

#     text = message.content

#     # Ignore trims / updates / management
#     if is_trim_or_update(text):
#         return

#     contract = parse_bear_contract(text)
#     if not contract:
#         return

#     entry_price = extract_entry_price(text)
#     if entry_price is None:
#         return  # No entry = already in trade

#     symbol = contract["symbol"]

#     if symbol in OPEN_TRADES:
#         return

#     if not is_price_close_to_entry(symbol, entry_price):
#         return

#     try:
#         qty = calculate_position_size(entry_price)
#         place_trade(symbol, qty, entry_price)

#         OPEN_TRADES.add(symbol)

#         msg = (
#             f"🚀 NEW TRADE EXECUTED\n\n"
#             f"Symbol: {symbol}\n"
#             f"Contracts: {qty}\n"
#             f"Entry: {entry_price}\n"
#             f"Stop Loss: {round(entry_price * (1 - STOP_LOSS_PERCENT), 2)}\n"
#         )

#         await message.channel.send(msg)
#         send_trade_email("🚨 Bear Bot Trade Executed", msg)

#     except Exception as e:
#         await message.channel.send(f"❌ Trade Failed: {e}")
#         send_trade_email("❌ Bear Bot Trade Failed", str(e))

# ---------------- START ---------------- #

# def start_discord():
#     client.run(DISCORD_TOKEN)

# if __name__ == "__main__":
#     start_discord()


# ---------------- EMAIL ---------------- #

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

























# ==================================old======================================

# ---------------- EMAIL ---------------- #

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
    
#     signal = parse_bear_signal(message.content)

#     if signal:
#         try:
#             api = get_api()

#             order = api.submit_order(
#                 symbol=signal["symbol"],
#                 qty=1,
#                 side="buy",
#                 type="market",
#                 time_in_force="day"
#             )

#             trade_msg = (
#                 f"Trade Placed Successfully 🚀\n\n"
#                 f"Symbol: {signal['symbol']}\n"
#                 f"Expiry: {signal['expiry']}\n"
#                 f"Strike: {signal['strike']}\n"
#                 f"Type: {signal['type'].upper()}\n"
#             )

#             await message.channel.send(f"✅ {trade_msg}")

#             send_trade_email(
#                 subject="🚨 Trading Bot Alert – Trade Executed",
#                 body=trade_msg
#             )

#         except Exception as e:
#             await message.channel.send(f"❌ Trade Failed: {e}")

#             send_trade_email(
#                 subject="❌ Trading Bot Alert – Trade Failed",
#                 body=str(e)
#             )

# # ---------------- START ---------------- #

# def start_discord():
#     client.run(DISCORD_TOKEN)

# if __name__ == "__main__":
#     start_discord()