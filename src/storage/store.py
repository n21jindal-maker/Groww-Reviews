import json
import os
from pathlib import Path
from typing import List, Set
from src.models import Review
from src.config import config
import datetime

def get_reviews_dir() -> Path:
    base_dir = Path(__file__).resolve().parent.parent.parent
    reviews_dir = base_dir / config['storage']['reviews_dir']
    reviews_dir.mkdir(parents=True, exist_ok=True)
    return reviews_dir

def get_pulses_dir() -> Path:
    base_dir = Path(__file__).resolve().parent.parent.parent
    pulses_dir = base_dir / config['storage']['pulses_dir']
    pulses_dir.mkdir(parents=True, exist_ok=True)
    return pulses_dir

def save_reviews(reviews: List[Review]):
    if not reviews:
        return
        
    reviews_dir = get_reviews_dir()
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    file_path = reviews_dir / f"{date_str}.json"
    
    # Load existing if file exists
    existing_reviews = []
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing_reviews = [Review(**r) for r in data]
        except json.JSONDecodeError:
            print(f"Warning: Could not read {file_path}. It might be corrupted.")
            
    # Deduplicate before saving
    existing_ids = {r.reviewId for r in existing_reviews}
    new_reviews = [r for r in reviews if r.reviewId not in existing_ids]
    
    if not new_reviews:
        return
        
    all_reviews = existing_reviews + new_reviews
    
    # Write to a tmp file first then rename for atomic write
    tmp_path = file_path.with_suffix('.tmp')
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in all_reviews], f, indent=2, ensure_ascii=False)
    
    tmp_path.replace(file_path)

def get_review_ids() -> Set[str]:
    """Returns a set of all review IDs currently stored across all files."""
    reviews_dir = get_reviews_dir()
    ids = set()
    for file_path in reviews_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for r in data:
                    ids.add(r['reviewId'])
        except json.JSONDecodeError:
            continue
    return ids

def load_reviews(weeks_ago: int = 12) -> List[Review]:
    """Loads reviews from the last N weeks."""
    reviews_dir = get_reviews_dir()
    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(weeks=weeks_ago)
    
    reviews = []
    for file_path in reviews_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for r_dict in data:
                    # Filter by date
                    r_at = datetime.datetime.fromisoformat(r_dict['at'])
                    if r_at.tzinfo is None:
                        r_at = r_at.replace(tzinfo=datetime.timezone.utc)
                        
                    if r_at >= cutoff_date:
                        reviews.append(Review(**r_dict))
        except (json.JSONDecodeError, ValueError, KeyError):
            continue
            
    return reviews

def save_pulse(pulse_md: str, date_str: str = None):
    pulses_dir = get_pulses_dir()
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    file_path = pulses_dir / f"{date_str}.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(pulse_md)
