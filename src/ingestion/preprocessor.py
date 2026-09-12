import re
from typing import List, Dict, Any

def remove_pii(text: str) -> str:
    """
    Remove basic PII from text.
    """
    if not text:
        return ""
    # Email
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[email]', text)
    # Phone number (naive)
    text = re.sub(r'\b\d{10}\b', '[phone]', text)
    # Could add more if needed
    return text

def normalize_text(text: str) -> str:
    """
    Normalize text: lowercasing, stripping whitespace.
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def deduplicate_reviews(reviews: List[Dict[str, Any]], existing_ids: set) -> List[Dict[str, Any]]:
    """
    Remove reviews that we already have.
    """
    unique_reviews = []
    seen = set()
    for r in reviews:
        rid = r.get("reviewId")
        if rid and rid not in existing_ids and rid not in seen:
            unique_reviews.append(r)
            seen.add(rid)
    return unique_reviews

def preprocess(raw_reviews: List[Dict[str, Any]], existing_ids: set) -> List[Dict[str, Any]]:
    deduped = deduplicate_reviews(raw_reviews, existing_ids)
    for r in deduped:
        clean_text = remove_pii(r.get("text", ""))
        clean_text = normalize_text(clean_text)
        r["text"] = clean_text
    return deduped
