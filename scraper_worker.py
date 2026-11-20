import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote_plus

# Live Base44 Claim Heads Webhook Endpoint
WEBHOOK_URL = "https://quizzical-claim-master-flow.base44.app/functions/ingestLead"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

SEARCH_TARGETS = [
    {"category": "Property Manager", "zip_code": "33157", "location": "Cutler Bay FL"},
    {"category": "Property Manager", "zip_code": "33156", "location": "Pinecrest FL"},
    {"category": "Roofer", "zip_code": "33157", "location": "Palmetto Bay FL"},
    {"category": "HOA Management", "zip_code": "33176", "location": "Miami FL"},
    {"category": "Restoration", "zip_code": "33176", "location": "Miami FL"}
]

def extract_phone(text):
    match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    return match.group(0) if match else "N/A"

def extract_email(text, fallback_domain):
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else f"info@{fallback_domain}.com"

def send_to_base44(payload):
    try:
        res = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if res.status_code == 200 and res.json().get("status") == "duplicate":
            print(f"  [=] Already in Claim Heads (skipped): {payload['business_name']}")
            return False
        elif res.status_code == 201:
            data = res.json()
            lead_id = data.get("id", "OK")
            b_name = payload["business_name"]
            b_phone = payload["phone"]
            print(f"  [+] Live in Claim Heads (ID: {lead_id}): {b_name} | {b_phone}")
            return True
        else:
            print(f"  [-] Rejected ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"  [-] Connection error: {e}")
        return False

def scrape_source(target, source_name, query_suffix=""):
    category = target["category"]
    zip_code = target["zip_code"]
    location = target["location"]

    query = f"{category} {location} {zip_code} {query_suffix}".strip()
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    print(f"[*] [{source_name}] Searching: {category} in {location} ({zip_code})...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"[-] HTTP {response.status_code} from search engine.")
            return 0

        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.select(".result")

        count = 0
        seen_names = set()

        for item in results:
            title_el = item.select_one(".result__title a")
            snippet_el = item.select_one(".result__snippet")

            if not title_el:
                continue

            raw_title = title_el.get_text(strip=True)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            link = title_el.get("href", "")

            clean_name = re.sub(r"(-|\||:).*$", "", raw_title).strip()
            if (
                len(clean_name) < 4
                or clean_name.lower() in seen_names
                or any(skip in clean_name.lower() for skip in ["top 10", "best ", "yelp", "yellowpages", "angi", "homeadvisor", "thumbtack"])
            ):
                continue

            seen_names.add(clean_name.lower())
            phone = extract_phone(snippet)
            clean_domain = re.sub(r"[^\w]", "", clean_name.lower())[:18] or "leadcontact"
            email = extract_email(snippet, clean_domain)

            payload = {
                "business_name": f"{clean_name} ({source_name})",
                "category": category,
                "zip_code": zip_code,
                "phone": phone,
                "email": email,
                "address": f"{location}, FL {zip_code}",
                "website": link if link.startswith("http") else f"https://www.{clean_domain}.com"
            }

            if send_to_base44(payload):
                count += 1
                time.sleep(0.4)

        print(f"[✔] [{source_name}] Total pushed for {category} ({zip_code}): {count}\n")
        return count

    except Exception as e:
        print(f"[-] Error scraping {source_name}: {e}\n")
        return 0

if __name__ == "__main__":
    print("=== Starting Multi-Platform B2B Lead Stream -> Claim Heads (Base44) ===\n")
    total_pushed = 0

    for target in SEARCH_TARGETS:
        total_pushed += scrape_source(target, "Web Directory", "phone email contact")
        time.sleep(1.5)

        total_pushed += scrape_source(target, "Facebook", "site:facebook.com")
        time.sleep(1.5)

        total_pushed += scrape_source(target, "Nextdoor", "site:nextdoor.com")
        time.sleep(1.5)

        total_pushed += scrape_source(target, "Reddit", "site:reddit.com/r/Miami OR site:reddit.com/r/florida")
        time.sleep(2)

    print(f"=== Sync Complete! Total Live Leads Pushed to Base44: {total_pushed} ===")

