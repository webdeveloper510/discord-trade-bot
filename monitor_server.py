# import os

# def run_monitor():
#     port = int(os.environ.get("PORT", 8080))
#     app.run(host="0.0.0.0", port=port)


# from flask import Flask
# import os

# app = Flask(__name__)

# @app.route("/")
# def home():
#     return "Cloud Run OK"

# @app.route("/healthz")
# def healthz():
#     return "OK", 200

# def run_monitor():
#     port = int(os.environ.get("PORT", 8080))
#     app.run(host="0.0.0.0", port=port)



from flask import Flask, request
import os
from trade_executor import get_api
# from twilio.rest import Client as TwilioClient

app = Flask(__name__)

# --- Helper functions ---
# def send_sms(message):
#     try:
#         twilio_client = TwilioClient(os.getenv("TWILIO_ACCOUNT_SID"),
#                                      os.getenv("TWILIO_AUTH_TOKEN"))
#         twilio_client.messages.create(
#             body=message,
#             from_=os.getenv("TWILIO_FROM"),
#             to=os.getenv("SMS_TO")
#         )
#     except Exception as e:
#         print("SMS send failed:", e)

# --- Routes ---
@app.route("/")
def home():
    return "Cloud Run OK"

@app.route("/healthz")
def healthz():
    return "OK", 200

@app.route("/metrics")
def metrics():
    key = request.args.get("key")
    if key != os.getenv("METRICS_KEY"):
        return "Unauthorized", 403
    # Example metrics
    return {
        "trading_mode": os.getenv("TRADING_MODE"),
        "risk_percent": os.getenv("RISK_PERCENT"),
        "kill_switch": os.getenv("KILL_SWITCH")
    }

# @app.route("/kill")
# def kill():
#     key = request.args.get("key")
#     if key != os.getenv("METRICS_KEY"):
#         return "Unauthorized", 403
#     os.environ["KILL_SWITCH"] = "true"
#     send_sms("⚠️ Trading stopped via Kill Switch!")
#     return "Trading killed", 200

@app.route("/set-risk")
def set_risk():
    key = request.args.get("key")
    value = request.args.get("value")
    if key != os.getenv("METRICS_KEY"):
        return "Unauthorized", 403
    if value:
        os.environ["RISK_PERCENT"] = value
        return f"Risk set to {value}%", 200
    return "No value provided", 400

@app.route("/toggle-mode")
def toggle_mode():
    key = request.args.get("key")
    mode = request.args.get("mode")
    if key != os.getenv("METRICS_KEY"):
        return "Unauthorized", 403
    if mode in ["paper", "live"]:
        os.environ["TRADING_MODE"] = mode
        return f"Trading mode switched to {mode}", 200
    return "Invalid mode", 400

@app.route("/confirm-live")
def confirm_live():
    key = request.args.get("key")
    if key != os.getenv("METRICS_KEY"):
        return "Unauthorized", 403
    os.environ["TRADING_MODE"] = "live"
    return "Live trading confirmed", 200

def run_monitor():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)