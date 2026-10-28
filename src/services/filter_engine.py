class FilterEngine:
    def __init__(self, client_config):
        self.config = client_config

    def evaluate_lead(self, lead_data, client_key="HIT_RESTORATION"):
        target_client = self.config.get("clients", {}).get(client_key, {})
        keywords = target_client.get("keywords", [])
        
        content = f"{lead_data.get('title', '')} {lead_data.get('body', '')}".lower()
        matched_keywords = [kw for kw in keywords if kw.lower() in content]
        
        score = min(len(matched_keywords) * 0.4, 1.0)
        is_qualified = score >= target_client.get("min_intent_score", 0.7)
        
        return {
            "qualified": is_qualified,
            "score": score,
            "client": target_client.get("name", client_key),
            "matched_keywords": matched_keywords,
            "raw_lead": lead_data
        }