import requests
import time

# --- IMPORTANT ---
# Your Bot Token is correct.
BOT_TOKEN = "8459655122:AAHbrveXm-YJtUMA14wvBP-gEy0xABLMPjQ"

def get_chat_id():
    """
    Retrieves the chat ID of the first person who messages the bot.
    """
    print("Bot is waiting for a message...")
    print("Please go to your bot on Telegram and send it ANY message now.")
    
    URL = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    update_id = 0
    
    # Check for new messages in a loop
    while True:
        try:
            response = requests.get(f"{URL}?offset={update_id + 1}", timeout=10).json()
            if response.get('result'):
                # Message found!
                chat_id = response['result'][0]['message']['chat']['id']
                print("\n-----------------------------------")
                print(f"✅ CHAT ID FOUND: {chat_id}")
                print("-----------------------------------")
                print("You can now stop this script (Ctrl+C).")
                print("Copy this ID and paste it into your 'telegram_alert.py' script.")
                return
            
            time.sleep(1)
        except requests.RequestException as e:
            print(f"Network error: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Please double-check that your BOT_TOKEN is correct and try again.")
            return

# --- THIS IS THE CORRECTED PART ---
# The if/else is removed. We now call the function directly.
if __name__ == "__main__":
    get_chat_id()