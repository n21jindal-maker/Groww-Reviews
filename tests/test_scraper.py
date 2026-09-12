import pytest
from src.ingestion.scraper import fetch_reviews

def test_fetch_reviews():
    # Test a small count to avoid long network calls in tests
    try:
        reviews = fetch_reviews("com.nextbillion.groww", max_count=5, weeks_ago=52)
        assert isinstance(reviews, list)
        if len(reviews) > 0:
            assert "reviewId" in reviews[0]
            assert "content" in reviews[0]
            assert "score" in reviews[0]
    except RuntimeError as e:
        pytest.skip(f"Network error during fetch_reviews: {e}")

def test_fetch_reviews_empty_app_id():
    with pytest.raises(ValueError):
        fetch_reviews("")
