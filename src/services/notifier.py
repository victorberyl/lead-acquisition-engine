import os
from twilio.rest import Client

class Notifier:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_phone = os.getenv("TWILIO_PHONE_NUMBER")
        self.to_phone = os.getenv("ALERT_PHONE_NUMBER")

    def send_lead_alert(self, lead_summary):
        print(f"\n[ALERT NOTIFIER] Qualified Lead Found for {lead_summary.get('client')}:")
        print(f"-> Title: {lead_summary['raw_lead'].get('title')}")
        print(f"-> Score: {lead_summary.get('score')}")
        print(f"-> Matched Keywords: {lead_summary.get('matched_keywords')}")

        has_valid_creds = (
            self.account_sid and 
            self.auth_token and 
            "your_twilio" not in self.account_sid.lower()
        )

        if has_valid_creds:
            try:
                client = Client(self.account_sid, self.auth_token)
                message_body = f"🚀 High-Intent Lead for {lead_summary.get('client')}!\nTitle: {lead_summary['raw_lead'].get('title')}\nURL: {lead_summary['raw_lead'].get('url')}"
                client.messages.create(
                    body=message_body,
                    from_=self.from_phone,
                    to=self.to_phone
                )
                print("[Notifier] SMS alert dispatched successfully via Twilio.")
            except Exception as e:
                print(f"[Notifier] Failed to send SMS via Twilio: {e}")
        else:
            print("[Notifier] Twilio credentials are using placeholders. Alert successfully logged to console (Mock SMS mode active).")