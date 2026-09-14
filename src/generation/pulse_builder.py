import datetime
import time
from typing import List, Tuple
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import GoogleAPIError
from src.models import ClusteringResult, ActionIdea
from src.config import config

PULSE_BUILDER_PROMPT = ChatPromptTemplate.from_template("""You are a communications specialist summarizing user feedback into a crisp, concise Weekly Pulse note.

Your task is to take the provided raw pulse text and condense/rewrite it so that it is under 250 words, while maintaining the exact structure, all 3 themes, all 3 quotes, and all 3 action ideas.
You MUST output the result in Markdown format. Keep the exact headings.

CRITICAL: The final output must be strictly LESS than 250 words. Be extremely concise.

Raw Pulse Text:
{raw_pulse}
""")

CONDENSE_PROMPT = ChatPromptTemplate.from_template("""The following Weekly Pulse note is too long (over 250 words). 
Please condense it to be strictly UNDER 250 words while keeping the exact same structure (Themes, Quotes, Action Ideas) and all 3 items in each section.

Markdown Pulse Note:
{pulse_text}
""")

def _get_llm():
    """Phase 4 LLM — Gemini (as per user requirement)."""
    return ChatGoogleGenerativeAI(
        model=config["gemini"]["model"],
        temperature=config["gemini"]["temperature"],
        google_api_key=config.get("GOOGLE_API_KEY", None),
        max_retries=config["gemini"]["max_retries"],
    )

def _invoke_with_retry(chain, inputs: dict, max_attempts: int = 5, initial_delay: float = 10.0) -> str:
    """Invoke a LangChain chain with exponential backoff on transient API errors (e.g. 503)."""
    delay = initial_delay
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return chain.invoke(inputs)
        except GoogleAPIError as e:
            last_exc = e
            if attempt < max_attempts:
                print(f"Warning: Gemini API error on attempt {attempt}/{max_attempts}: {e}. Retrying in {delay:.0f}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"Error: Gemini API call failed after {max_attempts} attempts.")
        except Exception as e:
            last_exc = e
            if attempt < max_attempts:
                print(f"Warning: Unexpected error on attempt {attempt}/{max_attempts}: {e}. Retrying in {delay:.0f}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"Error: Chain invocation failed after {max_attempts} attempts.")
    raise last_exc


def _load_template() -> str:
    template_path = Path(__file__).resolve().parent.parent.parent / "templates" / "pulse_template.md"
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

def build_pulse(themes: ClusteringResult, quotes: List[str], actions: List[ActionIdea], review_count: int, start_date: str, end_date: str) -> Tuple[str, str]:
    # 1. Format the raw text using the template
    template = _load_template()
    
    top_themes = themes.themes[:3]
    themes_str = "\n".join([f"{i+1}. {t.theme_name} ({t.count} mentions)" for i, t in enumerate(top_themes)])
    quotes_str = "\n".join([f"• \"{q}\"" for q in quotes[:3]])
    actions_str = "\n".join([f"{i+1}. {a.action}" for i, a in enumerate(actions[:3])])
    
    date_str = datetime.datetime.now().strftime("%b %d, %Y")
    
    raw_pulse = template.format(
        date=date_str,
        themes=themes_str,
        quotes=quotes_str,
        actions=actions_str,
        review_count=review_count,
        start_date=start_date,
        end_date=end_date
    )
    
    # 2. Use LLM to ensure it's well-written and under 250 words
    llm = _get_llm()
    chain = PULSE_BUILDER_PROMPT | llm | StrOutputParser()
    
    pulse_md = _invoke_with_retry(chain, {"raw_pulse": raw_pulse})
    
    # 3. Word count validation and condense loop
    word_count = len(pulse_md.split())
    if word_count > 250:
        print(f"Warning: Pulse is {word_count} words. Condensing...")
        condense_chain = CONDENSE_PROMPT | llm | StrOutputParser()
        pulse_md = _invoke_with_retry(condense_chain, {"pulse_text": pulse_md})
        
        new_word_count = len(pulse_md.split())
        if new_word_count > 250:
            print(f"Warning: Pulse is still over limit after condensing ({new_word_count} words).")
            
    # Create plain-text version by removing basic markdown
    pulse_text = pulse_md.replace("📊 ", "").replace("🔍 ", "").replace("💬 ", "").replace("🎯 ", "").replace("📅 ", "").replace("**", "")
    
    return pulse_md, pulse_text
