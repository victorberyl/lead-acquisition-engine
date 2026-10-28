from flask import Blueprint, request, jsonify

meta_webhook_bp = Blueprint("meta_webhook", __name__)

@meta_webhook_bp.route("/webhook/meta", methods=["GET", "POST"])
def handle_meta_lead():
    if request.method == "GET":
        # Meta Webhook Verification
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        if mode == "subscribe" and token == "HIT_PEGASUS_SECRET":
            return challenge, 200
        return "Verification failed", 403

    elif request.method == "POST":
        data = request.json
        print(f"[Meta Lead Webhook] Received payload: {data}")
        return jsonify({"status": "received"}), 200