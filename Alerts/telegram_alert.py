import requests

# --- IMPORTANT ---
# Paste your own Bot Token and Chat ID here
BOT_TOKEN = "8459655122:AAHbrveXm-YJtUMA14wvBP-gEy0xABLMPjQ"
CHAT_ID = "1362872793"

def send_alert(message="Ambulance detected! Clearing route."):
    """
    Sends a message to your Telegram account via your bot.
    """
    # This is the URL for the Telegram Bot API
    url = f"https://api.telegram.org/bot{B8459655122:AAHbrveXm-YJtUMA14wvBP-gEy0xABLMPjQ}/sendMessage"
    
    # This is the data we are sending
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    
    try:
        # Send the request
        response = requests.post(url, json=payload)
        # Check if it was successful
        if response.status_code == 200:
            print("Alert sent successfully!")
        else:
            print(f"Failed to send alert. Status code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

# This part allows us to test the script directly
if __name__ == "__main__":
    send_alert("This is a test alert from my Python script! 🚨")