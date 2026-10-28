import requests

class RedditScraper:
    def __init__(self):
        # Updated browser headers to bypass basic bot filtering
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }

    def fetch_posts(self, subreddit_name, keywords, limit=25):
        url = f"https://www.reddit.com/r/{subreddit_name}/new.json?limit={limit}"
        posts = []
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                children = data.get("data", {}).get("children", [])
                
                for child in children:
                    post_data = child.get("data", {})
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")
                    full_text = f"{title} {selftext}".lower()
                    
                    if any(kw.lower() in full_text for kw in keywords):
                        posts.append({
                            "id": post_data.get("id"),
                            "title": title,
                            "author": post_data.get("author"),
                            "url": f"https://reddit.com{post_data.get('permalink')}",
                            "body": selftext
                        })
            else:
                print(f"[RedditScraper] HTTP {response.status_code} when fetching r/{subreddit_name} (Using mock fallback)")
                posts = self._get_mock_posts(subreddit_name)
        except Exception as e:
            print(f"[RedditScraper] Error fetching r/{subreddit_name}: {e} (Using mock fallback)")
            posts = self._get_mock_posts(subreddit_name)
            
        return posts

    def _get_mock_posts(self, subreddit_name):
        return [
            {
                "id": f"mock_{subreddit_name}_1",
                "title": f"Need immediate help with water damage and mold in my basement in r/{subreddit_name}",
                "author": "homeowner_alert",
                "url": f"https://reddit.com/r/{subreddit_name}/mock_post_1",
                "body": "Insurance company denied claim for flood restoration. Looking for a public adjuster."
            }
        ]