import requests
import json
from twilio.rest import Client

class Notifier:
    def __init__(self, config=None):
        self.config = config or {}
        self.twilio_cfg = self.config.get("twilio", {})
        self.base44_cfg = self.config.get("base44", {})

    def send_lead_alert(self, lead_data):
        """Dispatches qualified lead alerts to both Twilio SMS and Base44 backend."""
        print(f"\n[Notifier] === QUALIFIED LEAD DETECTED ===")
        print(f"Title: {lead_data.get('title')}")
        print(f"Source: {lead_data.get('source')}")
        print(f"Score: {lead_data.get('score')}")
        
        # 1. Dispatch SMS via Twilio
        self._send_sms(lead_data)
        
        # 2. Dispatch to Base44 Application
        self._send_to_base44(lead_data)

    def _send_sms(self, lead_data):
        sid = self.twilio_cfg.get("account_sid")
        token = self.twilio_cfg.get("auth_token")
        from_phone = self.twilio_cfg.get("phone_number")
        
        if not sid or sid == "YOUR_SID_HERE":
            print("[Notifier - Twilio] Using mock SMS output (placeholder credentials detected).")
            return
            
        try:
            client = Client(sid, token)
            body = (
                f"?? [NEW LEAD MATCH]\n"
                f"Source: {lead_data.get('source')}\n"
                f"Author: {lead_data.get('author')}\n"
                f"Title: {lead_data.get('title')}\n"
                f"Link: {lead_data.get('url')}"
            )
            # Default recipient phone (can be updated dynamically in config)
            message = client.messages.create(
                body=body,
                from_=from_phone,
                to=from_phone 
            )
            print(f"[Notifier - Twilio] SMS sent successfully! SID: {message.sid}")
        except Exception as e:
            print(f"[Notifier - Twilio Error]: {e}")

    def _send_to_base44(self, lead_data):
        url = self.base44_cfg.get("webhook_url")
        token = self.base44_cfg.get("api_token")
        
        if not url or "robert-app.base44.app" in url:
            print("[Notifier - Base44] Base44 endpoint in mock/placeholder mode.")
            return

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.post(url, json=lead_data, headers=headers, timeout=5)
            if response.status_code in [200, 201]:
                print(f"[Notifier - Base44] Lead successfully pushed to Base44 database!")
            else:
                print(f"[Notifier - Base44] Failed with status code: {response.status_code}")
        except Exception as e:
            print(f"[Notifier - Base44 Error]: {e}")
