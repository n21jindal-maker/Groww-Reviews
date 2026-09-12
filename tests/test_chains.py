import pytest
from unittest.mock import patch, MagicMock
from src.models import Review, ClusteringResult, ThemeAssignment, ActionIdea
from src.analysis.chains import analyze_themes, select_quotes, generate_action_ideas
from src.analysis.parsers import ActionIdeas

@pytest.fixture
def sample_reviews():
    return [
        Review(reviewId="1", score=1, text="App crashes on login", at="2026-09-01T10:00:00+00:00"),
        Review(reviewId="2", score=2, text="UI is confusing and slow", at="2026-09-01T10:00:00+00:00"),
    ]

@pytest.fixture
def mock_themes():
    return ClusteringResult(themes=[
        ThemeAssignment(theme_name="Performance", review_ids=["1"], count=1),
        ThemeAssignment(theme_name="Usability", review_ids=["2"], count=1)
    ])

@patch('src.analysis.chains.get_llm')
def test_analyze_themes(mock_get_llm, sample_reviews):
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    # Mock chain invocation returning a ClusteringResult
    # LangChain chains can be mocked directly at the invoke level
    with patch('langchain_core.runnables.base.RunnableSequence.invoke') as mock_invoke:
        mock_invoke.return_value = ClusteringResult(themes=[
            ThemeAssignment(theme_name="Test Theme", review_ids=["1", "2"], count=2)
        ])
        
        result = analyze_themes(sample_reviews)
        assert len(result.themes) == 1
        assert result.themes[0].theme_name == "Test Theme"
        assert result.themes[0].count == 2

@patch('src.analysis.chains.get_llm')
def test_select_quotes(mock_get_llm, sample_reviews, mock_themes):
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    with patch('langchain_core.runnables.base.RunnableSequence.invoke') as mock_invoke:
        mock_invoke.return_value = "App crashes on login"
        
        quotes = select_quotes(mock_themes, sample_reviews)
        assert len(quotes) == 2 # Top 2 themes in fixture
        assert quotes[0] == "App crashes on login"

@patch('src.analysis.chains.get_llm')
def test_generate_action_ideas(mock_get_llm, mock_themes):
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm
    
    with patch('langchain_core.runnables.base.RunnableSequence.invoke') as mock_invoke:
        mock_invoke.return_value = ActionIdeas(actions=[
            ActionIdea(theme_name="Performance", action="Fix crash"),
            ActionIdea(theme_name="Usability", action="Redesign UI"),
            ActionIdea(theme_name="General", action="General fixes")
        ])
        
        actions = generate_action_ideas(mock_themes)
        assert len(actions) == 3
        assert actions[0].action == "Fix crash"
