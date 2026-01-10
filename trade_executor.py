import os
import alpaca_trade_api as tradeapi

def get_api():
    base = "https://api.alpaca.markets" if os.getenv("TRADING_MODE") == "live" \
        else "https://paper-api.alpaca.markets"

    return tradeapi.REST(
        os.getenv("ALPACA_API_KEY"),
        os.getenv("ALPACA_SECRET_KEY"),
        base_url=base
    )
    

