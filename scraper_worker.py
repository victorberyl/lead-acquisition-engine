import os
import re
import sys
import time
import json
import requests

# --- CONFIGURATION ---
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "").strip()
INGEST_URL = "https://claimhadesapp.1000mech.com/api/functions/ingestLead"
LOG_RUN_URL = "https://claimhadesapp.1000mech.com/api/functions/logScraperRun"

TARGETS = [
    {"category": "Roofing", "city": "Miami", "state": "FL", "zip": "33101"},
    {"category": "Plumbing", "city": "Miami", "state": "FL", "zip": "33125"},
    {"category": "Restoration", "city": "Miami", "state": "FL", "zip": "33176"},
    {"category": "HVAC", "city": "Fort Lauderdale", "state": "FL", "zip": "33301"},
    {"category": "General Contractor", "city": "West Palm Beach", "state": "FL", "zip": "33401"},
]

PLATFORMS = [
    {"name": "Web Directory", "site_filter": ""},
    {"name": "Facebook", "site_filter": "site:facebook.com "},
    {"name": "Nextdoor", "site_filter": "site:nextdoor.com "},
    {"name": "Reddit", "site_filter": "site:reddit.com "},
]

PHONE_REGEX = re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def search_serper(query: str, stats: dict) -> list:
    if not SERPER_API_KEY:
        print("[!] Missing SERPER_API_KEY environment variable.")
        stats["errors"] += 1
        return []

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": 10}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code == 429:
            print("[!] Serper rate limit (HTTP 429). Cooling down 10s...")
            stats["http_blocks"] += 1
            time.sleep(10)
            resp = requests.post(url, headers=headers, json=payload, timeout=20)

        if resp.status_code != 200:
            print(f"[-] Serper error (HTTP {resp.status_code}): {resp.text[:120]}")
            stats["http_blocks"] += 1
            return []

        data = resp.json()
        return data.get("organic", [])
    except Exception as exc:
        print(f"[-] Request exception: {exc}")
        stats["errors"] += 1
        return []


def clean_business_name(title: str, platform: str) -> str:
    name = title.split("|")[0].split(" - ")[0].strip()
    if platform == "Facebook":
        name = re.sub(r"\s*-\s*Home\s*$", "", name, flags=re.I)
    return name[:100].strip() or "Local Contractor"


def ingest_lead(lead_payload: dict, stats: dict):
    try:
        resp = requests.post(INGEST_URL, json=lead_payload, timeout=15)
        if resp.status_code == 201:
            stats["new_leads"] += 1
            src = lead_payload["source"]
            stats["by_source"][src] = stats["by_source"].get(src, 0) + 1
            print(f"    [+] Added: {lead_payload['business_name']} ({src})")
        elif resp.status_code == 200:
            stats["duplicates"] += 1
        else:
            stats["errors"] += 1
            print(f"    [!] Ingest HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as exc:
        stats["errors"] += 1
        print(f"    [!] Ingest exception: {exc}")


def log_run_telemetry(stats: dict):
    if stats["new_leads"] > 0 and stats["errors"] == 0 and stats["http_blocks"] == 0:
        status = "Success"
    elif stats["new_leads"] > 0 or stats["duplicates"] > 0:
        status = "Partial"
    else:
        status = "Failed"

    telemetry = {
        "status": status,
        "new_leads": stats["new_leads"],
        "duplicates_skipped": stats["duplicates"],
        "http_blocks": stats["http_blocks"],
        "errors": stats["errors"],
        "source_breakdown": json.dumps(stats["by_source"]),
    }

    try:
        resp = requests.post(LOG_RUN_URL, json=telemetry, timeout=15)
        if resp.status_code in (200, 201):
            print("[✓] Telemetry logged to Claim Heads Admin Dashboard.")
        else:
            print(f"[!] Telemetry HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as exc:
        print(f"[!] Telemetry exception: {exc}")

    return status


def main():
    stats = {
        "new_leads": 0,
        "duplicates": 0,
        "http_blocks": 0,
        "errors": 0,
        "by_source": {p["name"]: 0 for p in PLATFORMS},
    }

    for target in TARGETS:
        for platform in PLATFORMS:
            q = (
                f"{platform['site_filter']}{target['category']} contractor "
                f"{target['city']} {target['state']} {target['zip']} phone"
            )
            print(f"[*] [{platform['name']}] Searching: {target['category']} in {target['city']} {target['state']} ({target['zip']})...")
            results = search_serper(q, stats)

            for item in results:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                combined_text = f"{title} {snippet}"

                phone_match = PHONE_REGEX.search(combined_text)
                email_match = EMAIL_REGEX.search(combined_text)
                phone = phone_match.group(0) if phone_match else ""
                email = email_match.group(0) if email_match else ""

                if not phone and not email:
                    continue

                business_name = clean_business_name(title, platform["name"])
                payload = {
                    "business_name": business_name,
                    "category": target["category"],
                    "phone": phone,
                    "email": email,
                    "city": target["city"],
                    "state": target["state"],
                    "zip": target["zip"],
                    "source": platform["name"],
                    "source_url": link,
                    "notes": snippet[:250],
                }
                ingest_lead(payload, stats)

            time.sleep(0.5)

    print("\n================ RUN SUMMARY ================")
    print(f"Status            : {'Success' if (stats['new_leads'] > 0 or stats['duplicates'] > 0) else 'Failed'}")
    print(f"New Leads Created : {stats['new_leads']}")
    print(f"Duplicates Skipped: {stats['duplicates']}")
    print(f"By Source         : {stats['by_source']}")
    print(f"HTTP Rate-Limits  : {stats['http_blocks']}")
    print(f"Webhook/Net Errors: {stats['errors']}")
    print("=============================================")

    final_status = log_run_telemetry(stats)
    if final_status == "Failed":
        print("CRITICAL: Workflow failed health check. Triggering GitHub alert!")
        sys.exit(1)


if __name__ == "__main__":
    main()