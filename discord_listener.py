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
    
    
    


import re
from datetime import datetime

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
    
    
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    signal = parse_bear_signal(message.content)
    if signal:
        await message.channel.send(f"📥 Bear Signal Detected: {signal}")

        try:
            api = get_api()

            order = api.submit_order(
                symbol=signal["symbol"],
                qty=1,
                side="buy",
                type="market",
                time_in_force="day"
            )

            await message.channel.send(
                f"✅ Trade Placed: {signal['symbol']} {signal['expiry']} "
                f"{signal['strike']}{signal['type'][0].upper()}"
            )
        except Exception as e:
            await message.channel.send(f"❌ Trade Failed: {e}")
    
    
    
def start_discord():
    token = os.getenv("DISCORD_TOKEN")
    client.run(token)    