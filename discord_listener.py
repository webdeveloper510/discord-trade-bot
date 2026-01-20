# import discord
# import os

# intents = discord.Intents.default()
# intents.message_content = True
# client = discord.Client(intents=intents)

# def start_discord():
#     client.run(os.getenv("DISCORD_TOKEN"))


# import discord
# import os

# intents = discord.Intents.default()
# intents.message_content = True
# client = discord.Client(intents=intents)

# @client.event
# async def on_ready():
#     print(f"Discord Bot logged in as {client.user}")

# def start_discord():
#     token = os.getenv("DISCORD_TOKEN")
#     client.run(token)

import os
import discord
from trade_executor import get_api

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Discord Bot logged in as {client.user}")

# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return

#     # --- Simple greeting ---
#     if message.content.lower() == "hi":
#         await message.channel.send(f"Hello {message.author.name}! Bot is working.")

#     # --- Check account balance ---
#     if message.content.lower() == "balance":
#         try:
#             api = get_api()
#             account = api.get_account()
#             await message.channel.send(
#                 f"Account Balance: ${account.cash} | Buying Power: ${account.buying_power} | Status: {account.status}"
#             )
#         except Exception as e:
#             await message.channel.send(f"Error fetching account info: {e}")

#     # --- Check open positions ---
#     if message.content.lower() == "positions":
#         try:
#             api = get_api()
#             positions = api.list_positions()
#             if positions:
#                 msg = "**Open Positions:**\n"
#                 for p in positions:
#                     msg += f"{p.symbol} - {p.qty} shares @ ${p.avg_entry_price}\n"
#             else:
#                 msg = "No open positions."
#             await message.channel.send(msg)
#         except Exception as e:
#             await message.channel.send(f"Error fetching positions: {e}")

#     # --- Example: Place a paper trade (buy 1 share of AAPL) ---
#     if message.content.lower() == "buy aapl":
#         try:
#             api = get_api()
#             order = api.submit_order(
#                 symbol="AAPL",
#                 qty=1,
#                 side="buy",
#                 type="market",
#                 time_in_force="day"
#             )
#             await message.channel.send(f"Order submitted: Buy 1 AAPL (paper trade)")
#         except Exception as e:
#             await message.channel.send(f"Error placing order: {e}")

# def start_discord():
#     token = os.getenv("DISCORD_TOKEN")
#     client.run(token)
    
    


# import re
# from datetime import datetime

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
    
    
# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return

#     signal = parse_bear_signal(message.content)
#     if signal:
#         await message.channel.send(f"📥 Bear Signal Detected: {signal}")

#         try:
#             api = get_api()

#             order = api.submit_order(
#                 symbol=signal["symbol"],
#                 qty=1,
#                 side="buy",
#                 type="market",
#                 time_in_force="day"
#             )

#             await message.channel.send(
#                 f"✅ Trade Placed: {signal['symbol']} {signal['expiry']} "
#                 f"{signal['strike']}{signal['type'][0].upper()}"
#             )
#         except Exception as e:
#             await message.channel.send(f"❌ Trade Failed: {e}")
    
    
    
# def start_discord():
#     token = os.getenv("DISCORD_TOKEN")
#     client.run(token)    
    
    
    
    

import os
import re
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import discord
from alpaca_trade_api import REST

# ---------------- CONFIG ---------------- #
SIGNAL_CHANNEL_ID = 1459267180859359357
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "pratish@codenomad.net")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "jldmjuduvlnvbrar")
ALERT_EMAIL_TO = "davinder@codenomad.net"

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

# ---------------- SIGNAL PARSER ---------------- #

def parse_bear_signal(text):
    pattern = r"Contract:\s*(\w+)\s+(\d{1,2}/\d{1,2})\s+(\d+)([CP])"
    match = re.search(pattern, text)

    if not match:
        return None

    symbol, exp, strike, opt_type = match.groups()
    year = datetime.now().year
    month, day = exp.split("/")

    return {
        "symbol": symbol,
        "expiry": f"{year}-{month.zfill(2)}-{day.zfill(2)}",
        "strike": strike,
        "type": "call" if opt_type == "C" else "put"
    }

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
    
    signal = parse_bear_signal(message.content)

    if signal:
        try:
            api = get_api()

            order = api.submit_order(
                symbol=signal["symbol"],
                qty=1,
                side="buy",
                type="market",
                time_in_force="day"
            )

            trade_msg = (
                f"Trade Placed Successfully 🚀\n\n"
                f"Symbol: {signal['symbol']}\n"
                f"Expiry: {signal['expiry']}\n"
                f"Strike: {signal['strike']}\n"
                f"Type: {signal['type'].upper()}\n"
            )

            await message.channel.send(f"✅ {trade_msg}")

            send_trade_email(
                subject="🚨 Trading Bot Alert – Trade Executed",
                body=trade_msg
            )

        except Exception as e:
            await message.channel.send(f"❌ Trade Failed: {e}")

            send_trade_email(
                subject="❌ Trading Bot Alert – Trade Failed",
                body=str(e)
            )

# ---------------- START ---------------- #

def start_discord():
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    start_discord()