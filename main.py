# from discord_listener import start_discord
# from monitor_server import run_monitor

# if __name__ == "__main__":
#     run_monitor()
#     start_discord()
    
    
    
    
# from monitor_server import run_monitor

# if __name__ == "__main__":
#     run_monitor()


from discord_listener import start_discord
from monitor_server import run_monitor
import threading

if __name__ == "__main__":
    # Start Discord bot in a separate thread
    threading.Thread(target=start_discord, daemon=True).start()
    
    # Start Flask monitoring server
    run_monitor()