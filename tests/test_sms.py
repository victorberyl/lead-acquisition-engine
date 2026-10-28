import os
import json
import sys

# Ensure Python can find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from twilio.rest import Client

def test_sms():
    print("--- [TEST] Checking Twilio SMS Integration ---")
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "default.json")
    
    if not os.path.exists(config_path):
        print("[Error] config/default.json not found. Please configure your credentials first.")
        return
        
    with open(config_path, "r") as f:
        config = json.load(f)
        
    twilio_cfg = config.get("twilio", {})
    sid = twilio_cfg.get("account_sid")
    token = twilio_cfg.get("auth_token")
    from_phone = twilio_cfg.get("phone_number")
    
    # Check if real credentials are present
    if not sid or sid == "YOUR_SID_HERE":
        print("[Skipped] Real Twilio credentials have not been configured yet (placeholder values detected).")
        print("Once Robert sends over the keys, update config/default.json and run this test again!")
        return
        
    to_phone = input("Enter destination mobile number to send test SMS (e.g., +15551234567): ")

    try:
        client = Client(sid, token)
        message = client.messages.create(
            body="[HIT Restoration & Pegasus] Lead acquisition engine test alert: SMS routing is operational!",
            from_=from_phone,
            to=to_phone
        )
        print(f"\n[Success!] Test SMS sent successfully. Message SID: {message.sid}")
    except Exception as e:
        print(f"\n[Twilio Error]: {e}")

if __name__ == "__main__":
    test_sms()
