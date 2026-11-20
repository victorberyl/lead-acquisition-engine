class RedditScraper:
    def __init__(self, config=None):
        self.config = config or {}

    def fetch_posts(self, subreddit=None, keywords=None):
        print("[INFO] Reddit public endpoints restricted. Skipping Reddit feed, focusing on Facebook & Nextdoor.")
        return []

    def fetch_leads(self, keywords=None):
        return self.fetch_posts(keywords=keywords)

def fetch_reddit_leads(keywords=None):
    scraper = RedditScraper()
    return scraper.fetch_posts(keywords=keywords)
