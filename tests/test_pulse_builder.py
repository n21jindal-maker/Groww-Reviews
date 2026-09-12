import pytest
from unittest.mock import patch, MagicMock
from src.models import ClusteringResult, ThemeAssignment, ActionIdea
from src.generation.pulse_builder import build_pulse

@pytest.fixture
def mock_themes():
    return ClusteringResult(themes=[
        ThemeAssignment(theme_name="Performance", review_ids=["1"], count=10),
        ThemeAssignment(theme_name="Usability", review_ids=["2"], count=5),
        ThemeAssignment(theme_name="Features", review_ids=["3"], count=2)
    ])

@pytest.fixture
def mock_quotes():
    return [
        "App is slow.",
        "Hard to navigate.",
        "Missing dark mode."
    ]

@pytest.fixture
def mock_actions():
    return [
        ActionIdea(theme_name="Performance", action="Fix slowness."),
        ActionIdea(theme_name="Usability", action="Improve nav."),
        ActionIdea(theme_name="Features", action="Add dark mode.")
    ]

@patch('src.generation.pulse_builder._get_llm')
def test_build_pulse(mock_get_llm, mock_themes, mock_quotes, mock_actions):
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    with patch('langchain_core.runnables.base.RunnableSequence.invoke') as mock_invoke:
        # Mock the LLM output
        mock_md = "📊 Groww Weekly Review Pulse\n\n🔍 TOP THEMES\n1. Performance\n2. Usability\n3. Features"
        mock_invoke.return_value = mock_md
        
        pulse_md, pulse_text = build_pulse(
            themes=mock_themes,
            quotes=mock_quotes,
            actions=mock_actions,
            review_count=100,
            start_date="Sep 01, 2026",
            end_date="Sep 07, 2026"
        )
        
        assert pulse_md == mock_md
        assert "📊" not in pulse_text # Plain text should have emojis stripped
        assert "Groww Weekly Review Pulse" in pulse_text

@patch('src.generation.pulse_builder._get_llm')
def test_build_pulse_condense_loop(mock_get_llm, mock_themes, mock_quotes, mock_actions):
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    with patch('langchain_core.runnables.base.RunnableSequence.invoke') as mock_invoke:
        # First call returns something over 250 words
        long_md = "Word " * 260
        # Second call returns condensed
        short_md = "Word " * 100
        
        mock_invoke.side_effect = [long_md, short_md]
        
        pulse_md, pulse_text = build_pulse(
            themes=mock_themes,
            quotes=mock_quotes,
            actions=mock_actions,
            review_count=100,
            start_date="Sep 01, 2026",
            end_date="Sep 07, 2026"
        )
        
        assert pulse_md == short_md
        assert mock_invoke.call_count == 2
