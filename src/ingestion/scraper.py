import datetime
from typing import List, Dict, Any
from google_play_scraper import Sort, reviews

def fetch_reviews(app_id: str = "com.nextbillion.groww", count: int = 50) -> List[Dict[str, Any]]:
    """
    Scrape reviews from the Google Play Store.
    Limited to 'count' (e.g. 50) to stay within TPM/RPM limits for LLM processing.
    """
    print(f"Fetching up to {count} reviews for {app_id}...")
    result, _ = reviews(
        app_id,
        lang='en', # English & Hinglish often show up here
        country='in', # India
        sort=Sort.NEWEST,
        count=count
    )
    
    # Standardize output to match our Pydantic Review model roughly
    raw_reviews = []
    for r in result:
        raw_reviews.append({
            "reviewId": r.get("reviewId"),
            "score": r.get("score"),
            "text": r.get("content", ""),
            "at": r.get("at").isoformat() if isinstance(r.get("at"), datetime.datetime) else str(r.get("at")),
            "appVersion": r.get("reviewCreatedVersion")
        })
        
    return raw_reviews
