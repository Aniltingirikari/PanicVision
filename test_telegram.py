import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

print(f"Bot Token: {BOT_TOKEN[:15]}... (hidden)" if BOT_TOKEN else "Bot Token: MISSING")
print(f"Chat ID: {CHAT_ID}" if CHAT_ID else "Chat ID: MISSING")

if not BOT_TOKEN or not CHAT_ID:
    print("❌ Missing credentials in .env file")
    print("Make sure .env file has:")
    print("TELEGRAM_BOT_TOKEN=your_token_here")
    print("TELEGRAM_CHAT_ID=your_chat_id_here")
else:
    # First, try to get bot info
    bot_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    try:
        bot_response = requests.get(bot_url, timeout=10)
        print(f"Bot Info: {bot_response.json()}")
    except Exception as e:
        print(f"Bot check failed: {e}")
    
    # Send test message
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": "🧪 Test message from PanicVision! Your alert system is working! ✅"
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Test message sent successfully! Check your Telegram.")
        else:
            print("❌ Failed to send message")
            print("Make sure:")
            print("1. You started a chat with your bot")
            print("2. The Chat ID is correct (from @userinfobot)")
            print("3. Bot token is correct")
    except Exception as e:
        print(f"❌ Error: {e}")