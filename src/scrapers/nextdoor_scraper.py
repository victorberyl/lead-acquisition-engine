import requests
import json

class NextdoorScraper:
    def __init__(self, session_token=None):
        self.session_token = session_token
        self.base_url = "https://nextdoor.com"

    def fetch_neighborhood_posts(self, neighborhood_slug, keywords):
        print(f"[NextdoorScraper] Scanning Nextdoor neighborhood: {neighborhood_slug}...")
        if not self.session_token:
            print(f"[NextdoorScraper] No session token provided. Using mock fallback for {neighborhood_slug}.")
            return self._get_mock_posts(neighborhood_slug, keywords)
        return []

    def _get_mock_posts(self, neighborhood_slug, keywords):
        return [
            {
                "title": f"Roof leak after heavy storm in {neighborhood_slug}",
                "text": "The storm last night caused a bad roof leak over our master bedroom. Shingles are missing and ceiling is stained. Looking for a reliable public adjuster or restoration contractor.",
                "source": f"Nextdoor: {neighborhood_slug}",
                "url": "https://nextdoor.com/p/mock-post-2",
                "author": "MockUser_ND"
            }
        ]
