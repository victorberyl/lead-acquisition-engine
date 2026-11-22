import sys
import json
import requests
from bs4 import BeautifulSoup
import time
import random
import re
from urllib.parse import quote_plus

WEBHOOK_URL = "https://quizzical-claim-master-flow.base44.app/functions/ingestLead"
LOG_WEBHOOK_URL = "https://quizzical-claim-master-flow.base44.app/functions/logScraperRun"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
]

SEARCH_TARGETS = [
    {"category": "Property Manager", "zip_code": "33157", "location": "Cutler Bay FL"},
    {"category": "Property Manager", "zip_code": "33156", "location": "Pinecrest FL"},
    {"category": "Roofer", "zip_code": "33157", "location": "Palmetto Bay FL"},
    {"category": "HOA Management", "zip_code": "33176", "location": "Miami FL"},
    {"category": "Restoration", "zip_code": "33176", "location": "Miami FL"}
]

JUNK_KEYWORDS = [
    "top 10", "best ", "yelp", "yellowpages", "angi", "homeadvisor", "thumbtack",
    "login", "sign up", "accedi", "facebook", "nextdoor", "reddit", "contact us",
    "what's changed", "guideline", "ads.", "how can i", "anyone ", "tell me why",
    "are there any", "a listing of", "to anyone living", "stuck in a", "home"
]

STATS = {
    "new_created": 0,
    "duplicates_skipped": 0,
    "rejected_errors": 0,
    "http_blocks": 0,
    "by_source": {
        "Web Directory": 0,
        "Facebook": 0,
        "Nextdoor": 0,
        "Reddit": 0
    }
}

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://duckduckgo.com/"
    }

def extract_phone(text):
    match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    return match.group(0) if match else ""

def extract_email(text, fallback_domain):
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else f"info@{fallback_domain}.com"

def is_valid_business(name):
    lower = name.lower().strip()
    if len(lower) < 5 or len(lower) > 65:
        return False
    if "?" in lower or lower.endswith("..."):
        return False
    if any(bad == lower or bad in lower for bad in JUNK_KEYWORDS):
        return False
    return True

def send_to_base44(payload, source_name):
    try:
        res = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if res.status_code == 200 and res.json().get("status") == "duplicate":
            STATS["duplicates_skipped"] += 1
            print(f"  [=] Duplicate skipped: {payload['business_name']}")
            return False
        elif res.status_code == 201:
            STATS["new_created"] += 1
            STATS["by_source"][source_name] = STATS["by_source"].get(source_name, 0) + 1
            lead_id = res.json().get("id", "OK")
            print(f"  [+] NEW Lead (ID: {lead_id}): {payload['business_name']} | {payload['phone'] or 'No Phone'}")
            return True
        else:
            STATS["rejected_errors"] += 1
            print(f"  [-] Webhook Error ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        STATS["rejected_errors"] += 1
        print(f"  [-] Connection Error: {e}")
        return False

def report_run_to_dashboard(run_status):
    log_payload = {
        "status": run_status,
        "new_leads": STATS["new_created"],
        "duplicates_skipped": STATS["duplicates_skipped"],
        "http_blocks": STATS["http_blocks"],
        "errors": STATS["rejected_errors"],
        "source_breakdown": json.dumps(STATS["by_source"])
    }
    try:
        res = requests.post(
            LOG_WEBHOOK_URL,
            json=log_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if res.status_code in (200, 201):
            print("[✔] Telemetry logged to Claim Heads Admin Dashboard.")
        else:
            print(f"[!] Could not log run telemetry ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"[!] Telemetry connection warning: {e}")

def scrape_source(target, source_name, query_suffix=""):
    category = target["category"]
    zip_code = target["zip_code"]
    location = target["location"]

    query = f"{category} {location} {zip_code} {query_suffix}".strip()
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    print(f"[*] [{source_name}] Searching: {category} in {location} ({zip_code})...")

    try:
        response = requests.get(url, headers=get_headers(), timeout=15)
        if response.status_code == 202:
            STATS["http_blocks"] += 1
            print("  [!] Rate limited (HTTP 202). Cooling down 25s...")
            time.sleep(25)
            response = requests.get(url, headers=get_headers(), timeout=15)

        if response.status_code != 200:
            STATS["http_blocks"] += 1
            print(f"  [-] Blocked/Failed (HTTP {response.status_code})")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.select(".result")
        seen_names = set()

        for item in results:
            title_el = item.select_one(".result__title a")
            snippet_el = item.select_one(".result__snippet")
            if not title_el:
                continue

            raw_title = title_el.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            link = title_el.get("href", "")

            clean_name = re.sub(r"(-|\||:|>|•).*$", "", raw_title).strip()
            if not is_valid_business(clean_name) or clean_name.lower() in seen_names:
                continue

            seen_names.add(clean_name.lower())
            phone = extract_phone(snippet)
            clean_domain = re.sub(r"[^\w]", "", clean_name.lower())[:18] or "leadcontact"
            email = extract_email(snippet, clean_domain)

            payload = {
                "business_name": f"{clean_name} ({source_name})",
                "category": category,
                "zip_code": zip_code,
                "phone": phone if phone else "N/A",
                "email": email,
                "address": f"{location}, FL {zip_code}",
                "website": link if link.startswith("http") else f"https://www.{clean_domain}.com"
            }

            send_to_base44(payload, source_name)
            time.sleep(0.5)

    except Exception as e:
        STATS["rejected_errors"] += 1
        print(f"  [-] Scrape Exception ({source_name}): {e}")

if __name__ == "__main__":
    print("=== Claim Heads B2B Lead Autopilot Run Started ===\n")

    for target in SEARCH_TARGETS:
        scrape_source(target, "Web Directory", "phone email contact")
        time.sleep(random.uniform(7, 10))

        scrape_source(target, "Facebook", "site:facebook.com")
        time.sleep(random.uniform(7, 10))

        scrape_source(target, "Nextdoor", "site:nextdoor.com/pages")
        time.sleep(random.uniform(7, 10))

        scrape_source(target, "Reddit", "site:reddit.com/r/Miami \"property management\" OR \"roofer\" OR \"HOA\"")
        time.sleep(random.uniform(8, 12))

    total_valid_seen = STATS["new_created"] + STATS["duplicates_skipped"]
    if total_valid_seen == 0 or STATS["rejected_errors"] > 3:
        run_status = "Failed"
    elif STATS["http_blocks"] > 0 or STATS["rejected_errors"] > 0:
        run_status = "Partial"
    else:
        run_status = "Success"

    print("\n================ RUN SUMMARY ================")
    print(f"Status              : {run_status}")
    print(f"New Leads Created   : {STATS['new_created']}")
    print(f"Duplicates Skipped  : {STATS['duplicates_skipped']}")
    print(f"By Source           : {STATS['by_source']}")
    print(f"HTTP Rate-Limits    : {STATS['http_blocks']}")
    print(f"Webhook/Net Errors  : {STATS['rejected_errors']}")
    print("=============================================")

    report_run_to_dashboard(run_status)

    if run_status == "Failed":
        print("CRITICAL: Workflow failed health check. Triggering GitHub alert!")
        sys.exit(1)
