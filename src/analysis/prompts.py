from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------------------------
# Token-minimal prompts for Groq openai/gpt-oss-120b (8K TPM limit)
#
# Design principles:
#   1. No PydanticOutputParser format_instructions (saves ~300–500 tokens/call).
#   2. Inline JSON schema as a short comment — LLM follows it reliably.
#   3. Prompt body is as short as possible while preserving accuracy.
# ---------------------------------------------------------------------------

THEME_CLUSTERING_PROMPT = ChatPromptTemplate.from_template(
    """Groww app analyst. Group reviews into AT MOST 5 themes. English or Hinglish. Cover pain points AND praise.

Return ONLY JSON, no markdown:
{{"themes":[{{"theme_name":"<label>","review_ids":["id1","id2",...],"count":<int>}}]}}

Reviews (reviewId | text):
{reviews_text}"""
)

CONSOLIDATION_PROMPT = ChatPromptTemplate.from_template(
    """Merge these Groww sub-themes into AT MOST 5 final themes. Combine review_ids lists. Rank by count descending.

Return ONLY JSON, no markdown:
{{"themes":[{{"theme_name":"<label>","review_ids":["id1",...],"count":<int>}}]}}

Sub-themes:
{sub_themes_text}"""
)

QUOTE_SELECTION_PROMPT = ChatPromptTemplate.from_template(
    """Theme: {theme_name}

Pick the single most representative English verbatim quote from the reviews below that best illustrates this theme.
Favor detailed, specific feedback over short generic comments (like "best app" or "please fix"). The quote should clearly reflect the specific context or reason behind the theme.
Return ONLY the quote text — no quotes marks, no explanation.

Reviews:
{reviews_text}"""
)

ACTION_IDEA_PROMPT = ChatPromptTemplate.from_template(
    """Based on these Groww user feedback themes, suggest exactly 3 specific actionable improvements.
Reference Groww features by name (e.g. Scalper mode, option chain, TradingView chart, F&O Lock, SIP).

Return ONLY a JSON object — no markdown, no explanation:
{{"actions":[{{"theme_name":"<theme>","action":"<concrete action>"}}]}}

Top themes:
{themes_summary}"""
)
