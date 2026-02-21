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
    



# pip install pytesseract pillow mss opencv-python numpy selenium webdriver-manager

# bear_bot_ocr/
# │
# ├── main.py
# ├── seen_signals.txt
# ├── config.py


# config.py

# # Screen capture area (adjust to your screen)
# CAPTURE_REGION = {
#     "top": 200,
#     "left": 300,
#     "width": 900,
#     "height": 600
# }

# DISCORD_CHANNEL_URL = "https://discord.com/channels/SERVER_ID/CHANNEL_ID"
# CHECK_INTERVAL_SECONDS = 60
# main.py
# import time
# import hashlib
# import pytesseract
# import cv2
# import numpy as np
# from mss import mss
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager
# from config import CAPTURE_REGION, DISCORD_CHANNEL_URL, CHECK_INTERVAL_SECONDS

# SEEN_FILE = "seen_signals.txt"

# # -------------------------------
# # Load seen hashes
# # -------------------------------
# def load_seen():
#     try:
#         with open(SEEN_FILE, "r") as f:
#             return set(line.strip() for line in f)
#     except FileNotFoundError:
#         return set()

# def save_hash(h):
#     with open(SEEN_FILE, "a") as f:
#         f.write(h + "\n")

# # -------------------------------
# # OCR Processing
# # -------------------------------
# def extract_signal(text):
#     lines = text.splitlines()

#     lotto = False
#     contract = None
#     entry = None

#     for line in lines:
#         line = line.strip()

#         if "LOTTO" in line.upper():
#             lotto = True

#         if "Contract:" in line:
#             contract = line.replace("Contract:", "").strip()

#         if "Entry:" in line:
#             entry = line.replace("Entry:", "").strip()

#     if lotto and contract and entry:
#         return f"LOTTO | {contract} | {entry}"

#     return None

# # -------------------------------
# # Capture Screen + OCR
# # -------------------------------
# def capture_and_ocr():
#     with mss() as sct:
#         img = np.array(sct.grab(CAPTURE_REGION))

#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]

#     text = pytesseract.image_to_string(gray)
#     return text

# # -------------------------------
# # Open Discord Automatically
# # -------------------------------
# def open_discord():
#     options = webdriver.ChromeOptions()
#     options.add_argument("--user-data-dir=./chrome_profile")
#     options.add_argument("--start-maximized")

#     driver = webdriver.Chrome(
#         service=Service(ChromeDriverManager().install()),
#         options=options
#     )

#     driver.get(DISCORD_CHANNEL_URL)
#     return driver

# # -------------------------------
# # MAIN LOOP
# # -------------------------------
# def main():
#     driver = open_discord()
#     time.sleep(15)  # Wait for Discord to load

#     seen_hashes = load_seen()

#     while True:
#         text = capture_and_ocr()
#         signal = extract_signal(text)

#         if signal:
#             signal_hash = hashlib.sha256(signal.encode()).hexdigest()

#             if signal_hash not in seen_hashes:
#                 seen_hashes.add(signal_hash)
#                 save_hash(signal_hash)

#                 print("\n🚨 NEW SIGNAL FOUND 🚨")
#                 print(signal)
#             else:
#                 print("⏩ Duplicate signal ignored")

#         else:
#             print("No valid LOTTO signal found")

#         time.sleep(CHECK_INTERVAL_SECONDS)

# if __name__ == "__main__":
#     main()


#333333333333333333333333333300------Live alpaca code -----------------


# key:- PKUKLN43KW5WEBVZ44G2IAFZCJ

# secret:- 4Cb77bRcVMVbhSzRfaJLbXjhteZ3LPhycRkroKatcgKv

