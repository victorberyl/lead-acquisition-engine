import os
import re
import sqlite3
import time
import requests
from bs4 import BeautifulSoup

DB_PATH = "base44_leads.db"

# Target search queries for HIT Restoration & Pegasus Public Adjusting outreach
TARGET_QUERIES = [
    "Property Management Companies in Cutler Bay FL",
    "Property Managers in Palmetto Bay FL",
    "HOA Management Companies in Pinecrest FL",
    "Roofing Contractors in South Florida",
    "Plumbing Companies in South Florida",
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS b2b_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL UNIQUE,
            category TEXT,
            zip_code TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            status TEXT DEFAULT 'New',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def extract_email_from_website(url):
    """Simple helper to scan a business website for contact emails."""
    if not url or not url.startswith("http"):
        return ""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=5)
        emails = re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", response.text
        )
        # Filter out common junk emails
        valid_emails = [
            e for e in set(emails) if not e.endswith((".png", ".jpg", ".jpeg"))
        ]
        return valid_emails[0] if valid_emails else ""
    except Exception:
        return ""


def save_lead(business_name, category, zip_code, address, phone, email, website):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO b2b_leads 
            (business_name, category, zip_code, address, phone, email, website)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                business_name,
                category,
                zip_code,
                address,
                phone,
                email,
                website,
            ),
        )
        conn.commit()
        if cursor.rowcount > 0:
            print(f"[+] Saved Lead: {business_name} | Phone: {phone}")
    except Exception as e:
        print(f"[-] Database Error: {e}")
    finally:
        conn.close()


def run_scraper():
    init_db()
    print("Starting B2B Lead Scraping Engine...")

    # Example scraping workflow (adaptable for Google Places API or direct directory parsing)
    for query in TARGET_QUERIES:
        print(f"\n--- Scraping Category: {query} ---")

        # Mock structured response for immediate local testing
        # Replace this block with your active web driver or API call endpoint
        sample_results = [
            {
                "name": "Biscayne Property Management",
                "category": "Property Manager",
                "zip": "33157",
                "address": "18495 S Dixie Hwy, Cutler Bay, FL",
                "phone": "(305) 555-0192",
                "website": "https://example.com",
                "email": "contact@biscaynepm.com",
            },
            {
                "name": "Palmetto Bay Roofing Experts",
                "category": "Roofer",
                "zip": "33157",
                "address": "9705 SW 160th St, Palmetto Bay, FL",
                "phone": "(305) 555-0144",
                "website": "",
                "email": "info@palmettoroofing.com",
            },
        ]

        for lead in sample_results:
            # If email is missing, attempt live scan on their domain
            if not lead["email"] and lead["website"]:
                lead["email"] = extract_email_from_website(lead["website"])

            save_lead(
                business_name=lead["name"],
                category=lead["category"],
                zip_code=lead["zip"],
                address=lead["address"],
                phone=lead["phone"],
                email=lead["email"],
                website=lead["website"],
            )

        time.sleep(1)


if __name__ == "__main__":
    run_scraper()