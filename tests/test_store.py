import pytest
import datetime
from src.models import Review
from src.storage.store import save_reviews, get_review_ids, load_reviews

def test_save_and_load(tmp_path, monkeypatch):
    # Mock get_reviews_dir to return a temporary path for isolated testing
    monkeypatch.setattr("src.storage.store.get_reviews_dir", lambda: tmp_path)
    
    dt = datetime.datetime.now(datetime.timezone.utc)
    reviews = [
        Review(reviewId="1", score=5, text="Good", at=dt.isoformat()),
        Review(reviewId="2", score=4, text="Okay", at=dt.isoformat())
    ]
    
    save_reviews(reviews)
    
    ids = get_review_ids()
    assert "1" in ids
    assert "2" in ids
    
    loaded = load_reviews(weeks_ago=1)
    assert len(loaded) == 2
    
def test_save_deduplicates(tmp_path, monkeypatch):
    monkeypatch.setattr("src.storage.store.get_reviews_dir", lambda: tmp_path)
    
    dt = datetime.datetime.now(datetime.timezone.utc)
    reviews = [
        Review(reviewId="1", score=5, text="Good", at=dt.isoformat())
    ]
    save_reviews(reviews)
    save_reviews(reviews) # Save again
    
    loaded = load_reviews(weeks_ago=1)
    assert len(loaded) == 1
