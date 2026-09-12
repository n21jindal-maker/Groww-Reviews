from src.ingestion.preprocessor import strip_pii, normalize_text, preprocess_reviews

def test_strip_email():
    assert strip_pii("Contact me at user@gmail.com") == "Contact me at [email]"

def test_strip_phone():
    assert strip_pii("Call +91-9876543210 now") == "Call [phone] now"
    assert strip_pii("My number 9876543210") == "My number [phone]"

def test_strip_username():
    assert strip_pii("@rahul_sharma posted this") == "[user] posted this"

def test_multiple_pii():
    text = "Call +919876543210 or email a@b.com"
    clean = strip_pii(text)
    assert "[phone]" in clean
    assert "[email]" in clean

def test_normalize_whitespace():
    assert normalize_text("  too   many    spaces  ") == "too many spaces"
    
def test_preprocess_reviews():
    raw_reviews = [
        {"reviewId": "1", "content": "Great app", "score": 5, "at": "2026-09-01T10:00:00+00:00"},
        {"reviewId": "2", "content": "  Email user@test.com  ", "score": 1, "at": "2026-09-02T10:00:00+00:00"},
        {"reviewId": "3", "content": "", "score": 3, "at": "2026-09-03T10:00:00+00:00"}, # Empty text
        {"reviewId": "1", "content": "Duplicate", "score": 5, "at": "2026-09-01T10:00:00+00:00"} # Duplicate ID
    ]
    
    clean = preprocess_reviews(raw_reviews)
    assert len(clean) == 2
    assert clean[0].reviewId == "1"
    assert clean[1].reviewId == "2"
    assert clean[1].text == "Email [email]"
