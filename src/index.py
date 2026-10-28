import os
import sys
import json
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

# Ensure Python can find modules inside src directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers.reddit_scraper import RedditScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.nextdoor_scraper import NextdoorScraper
from services.filter_engine import FilterEngine
from services.notifier import Notifier

app = Flask(__name__)

# Load Client Configuration
config_path = os.path.join(os.path.dirname(__file__), "..", "config", "default.json")
with open(config_path, "r") as f:
    client_config = json.load(f)

# Initialize Scrapers and Engines
reddit_scraper = RedditScraper()
facebook_scraper = FacebookScraper()
nextdoor_scraper = NextdoorScraper()
filter_engine = FilterEngine(client_config)
notifier = Notifier()

TARGET_SUBREDDITS = ["HomeImprovement", "DIY", "Plumbing", "insurance", "Homeowners"]
TARGET_FB_GROUPS = ["LocalHomeowners", "StormDamageRestoration"]
TARGET_NEIGHBORHOODS = ["downtown-metro", "suburb-heights"]
TARGET_KEYWORDS = ["water damage", "flood restoration", "mold", "public adjuster", "roof leak"]

def run_lead_acquisition_cycle():
    """Runs the full multi-platform scraping and lead processing pipeline."""
    print("\n--- [BACKGROUND JOB] STARTING MULTI-PLATFORM LEAD ACQUISITION CYCLE ---")
    
    all_posts = []

    # 1. Scrape Reddit
    for sub in TARGET_SUBREDDITS:
        all_posts.extend(reddit_scraper.fetch_posts(sub, TARGET_KEYWORDS))

    # 2. Scrape Facebook Groups
    for group in TARGET_FB_GROUPS:
        all_posts.extend(facebook_scraper.fetch_group_posts(group, TARGET_KEYWORDS))

    # 3. Scrape Nextdoor
    for neighborhood in TARGET_NEIGHBORHOODS:
        all_posts.extend(nextdoor_scraper.fetch_neighborhood_posts(neighborhood, TARGET_KEYWORDS))

    # Evaluate all collected leads through the filter engine
    for post in all_posts:
        evaluated_lead = filter_engine.evaluate_lead(post)
        if evaluated_lead and evaluated_lead.get("is_qualified"):
            notifier.send_lead_alert(evaluated_lead)
                
    print("--- [BACKGROUND JOB] MULTI-PLATFORM CYCLE COMPLETE ---\n")

# Setup APScheduler
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(run_lead_acquisition_cycle, 'interval', minutes=15)

@app.route('/webhook/meta', methods=['POST'])
def meta_webhook():
    """Endpoint for Meta / Facebook Lead Ads Webhook"""
    data = request.json
    print(f"\n[Meta Webhook Received]: {data}")
    return jsonify({"status": "success", "message": "Lead received"}), 200

if __name__ == '__main__':
    scheduler.start()
    run_lead_acquisition_cycle()
    print("\n[Flask Server] Starting web server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
