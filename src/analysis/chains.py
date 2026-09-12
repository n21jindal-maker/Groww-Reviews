import re
import time
import json
from typing import List, Dict, Tuple
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from src.config import config, GROQ_API_KEY
from src.models import Review, ClusteringResult, ActionIdea, ThemeAssignment
from src.analysis.prompts import (
    THEME_CLUSTERING_PROMPT,
    CONSOLIDATION_PROMPT,
    QUOTE_SELECTION_PROMPT,
    ACTION_IDEA_PROMPT,
)

# ---------------------------------------------------------------------------
# Groq openai/gpt-oss-120b limits: 8K TPM, 30 RPM, 1K RPD, 200K TPD
#
# Token budget per call (50 reviews, short IDs):
#   Input:  50 × ~28 tokens/review + ~60 prompt tokens ≈ 1,460 tokens
#   Output: ~800 tokens (5 themes × ~160 tokens each)
#   Total:  ~2,260 per batch call  ✓ well under 8K TPM
#
# Key optimisation: use short sequential IDs (R001..R150) instead of UUIDs
#   — saves ~24 tokens per review (36-char UUID vs 4-char short ID)
#   — saves ~1,200 tokens across 50-review batch
# ---------------------------------------------------------------------------
BATCH_SIZE = 50
INTER_CALL_SLEEP = 10  # seconds — conservative TPM buffer


def _get_groq_llm() -> ChatGroq:
    return ChatGroq(
        model=config["groq"]["model"],
        temperature=config["groq"]["temperature"],
        api_key=GROQ_API_KEY,
        max_retries=config["groq"]["max_retries"],
    )


def _extract_json(text: str) -> dict:
    """Robustly extract JSON dict from LLM output."""
    for s in [text.strip(), re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()]:
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _trim(text: str, max_words: int = 35) -> str:
    words = text.split()
    return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")


def _make_short_id(idx: int) -> str:
    """Convert 0-indexed position to short ID like R001."""
    return f"R{idx+1:03d}"


# ---------------------------------------------------------------------------
# Theme clustering — 3 batches of 50 reviews, short IDs, then consolidate
# ---------------------------------------------------------------------------

def analyze_themes(reviews: List[Review]) -> ClusteringResult:
    """
    Token-safe clustering for Groq 8K TPM:
    - Short IDs (R001..R150) instead of UUIDs → saves ~24 tok/review
    - Batches of 50 reviews → ~1,460 tokens input per call
    - Consolidation input: theme names + counts only (~150 tokens)
    - Post-consolidation: review IDs mapped back via short-ID → real UUID lookup
    """
    llm = _get_groq_llm()
    chain = THEME_CLUSTERING_PROMPT | llm | StrOutputParser()

    # Build global short_id → real_reviewId mapping
    short_to_real: Dict[str, str] = {
        _make_short_id(i): r.reviewId for i, r in enumerate(reviews)
    }

    batches = [reviews[i:i + BATCH_SIZE] for i in range(0, len(reviews), BATCH_SIZE)]
    all_sub_themes: List[ThemeAssignment] = []
    # short_theme_name → accumulated real review IDs
    id_accumulator: Dict[str, List[str]] = {}

    for b_idx, batch in enumerate(batches):
        if b_idx > 0:
            print(f"  Sleeping {INTER_CALL_SLEEP}s (TPM buffer)...")
            time.sleep(INTER_CALL_SLEEP)

        # Global offset for short IDs in this batch
        offset = b_idx * BATCH_SIZE
        reviews_text = "\n".join(
            f"{_make_short_id(offset + i)} | {_trim(r.text)}"
            for i, r in enumerate(batch)
        )
        print(f"  Batch {b_idx+1}/{len(batches)}: {len(batch)} reviews "
              f"(~{len(reviews_text)//4} input tokens)...")

        raw = chain.invoke({"reviews_text": reviews_text})
        data = _extract_json(raw)

        if not data.get("themes"):
            print(f"  Warning: batch {b_idx+1} returned empty themes. Raw={repr(raw[:100])}")

        for t in data.get("themes", []):
            short_ids = t.get("review_ids", [])
            # Map short IDs → real UUIDs
            real_ids = [short_to_real[sid] for sid in short_ids if sid in short_to_real]
            name = t.get("theme_name", "Unknown")
            count = t.get("count", len(real_ids))

            all_sub_themes.append(ThemeAssignment(
                theme_name=name,
                review_ids=real_ids,
                count=count,
            ))
            if name not in id_accumulator:
                id_accumulator[name] = []
            id_accumulator[name].extend(real_ids)

    if not all_sub_themes:
        print("  Warning: all batches returned empty. Check Groq API / TPM limits.")
        return ClusteringResult(themes=[])

    # --- Consolidation: names + counts only (~150 tokens) ---
    print(f"  Sleeping {INTER_CALL_SLEEP}s before consolidation...")
    time.sleep(INTER_CALL_SLEEP)

    consol_chain = CONSOLIDATION_PROMPT | llm | StrOutputParser()
    sub_themes_text = "\n".join(
        f"{t.theme_name} ({t.count})" for t in all_sub_themes
    )
    print(f"  Consolidating {len(all_sub_themes)} sub-themes...")
    raw_consol = consol_chain.invoke({"sub_themes_text": sub_themes_text})
    data_consol = _extract_json(raw_consol)

    final_themes: List[ThemeAssignment] = []
    for t in data_consol.get("themes", [])[:5]:
        merged_name = t.get("theme_name", "Unknown")
        merged_count = t.get("count", 0)
        # Re-map IDs: fuzzy word-intersection match between merged and sub-theme names
        merged_ids: List[str] = []
        m_words = set(merged_name.lower().split())
        for sub in all_sub_themes:
            s_words = set(sub.theme_name.lower().split())
            if m_words & s_words:  # any word overlap
                merged_ids.extend(sub.review_ids)
        # Deduplicate preserving order
        seen: set = set()
        deduped = [rid for rid in merged_ids if not (rid in seen or seen.add(rid))]
        final_themes.append(ThemeAssignment(
            theme_name=merged_name,
            review_ids=deduped,
            count=merged_count if merged_count > 0 else len(deduped),
        ))

    if not final_themes:
        print("  Consolidation returned empty — merging raw sub-themes by name as fallback.")
        merged_map: Dict[str, ThemeAssignment] = {}
        for t in all_sub_themes:
            key = t.theme_name.lower()
            if key in merged_map:
                merged_map[key].review_ids.extend(t.review_ids)
                merged_map[key].count += t.count
            else:
                merged_map[key] = ThemeAssignment(
                    theme_name=t.theme_name,
                    review_ids=list(t.review_ids),
                    count=t.count,
                )
        final_themes = list(merged_map.values())

    final_themes.sort(key=lambda t: t.count, reverse=True)
    return ClusteringResult(themes=final_themes[:5])


# ---------------------------------------------------------------------------
# Quote selection — 1 call per top theme
# ---------------------------------------------------------------------------

def select_quotes(themes: ClusteringResult, all_reviews: List[Review]) -> List[str]:
    """Cap at 10 reviews per theme, trim to 40 words."""
    llm = _get_groq_llm()
    chain = QUOTE_SELECTION_PROMPT | llm | StrOutputParser()

    review_map = {r.reviewId: r.text for r in all_reviews}
    quotes: List[str] = []

    for i, theme in enumerate(themes.themes[:3]):
        if i > 0:
            print(f"  Sleeping {INTER_CALL_SLEEP}s between quote calls...")
            time.sleep(INTER_CALL_SLEEP)

        texts = [review_map[rid] for rid in theme.review_ids if rid in review_map][:10]

        if not texts:
            quotes.append(f"No representative quote available for: {theme.theme_name}")
            continue

        reviews_text = "\n".join(f"- {_trim(t, 40)}" for t in texts)
        print(f"  Quote for '{theme.theme_name}' ({len(texts)} candidates)...")
        quote = chain.invoke({"theme_name": theme.theme_name, "reviews_text": reviews_text})
        quotes.append(quote.strip())

    return quotes


# ---------------------------------------------------------------------------
# Action ideas — single compact call
# ---------------------------------------------------------------------------

def generate_action_ideas(themes: ClusteringResult) -> List[ActionIdea]:
    """~300 tokens input, single call."""
    llm = _get_groq_llm()
    chain = ACTION_IDEA_PROMPT | llm | StrOutputParser()

    print(f"  Sleeping {INTER_CALL_SLEEP}s before action ideas call...")
    time.sleep(INTER_CALL_SLEEP)

    top_themes = themes.themes[:3]
    themes_summary = "\n".join(f"- {t.theme_name} ({t.count} mentions)" for t in top_themes)

    print("  Generating action ideas...")
    raw = chain.invoke({"themes_summary": themes_summary})
    data = _extract_json(raw)

    actions: List[ActionIdea] = []
    for a in data.get("actions", [])[:3]:
        actions.append(ActionIdea(
            theme_name=a.get("theme_name", ""),
            action=a.get("action", ""),
        ))

    if not actions:
        print("  Warning: action parsing failed, using fallbacks.")
        for t in top_themes:
            actions.append(ActionIdea(
                theme_name=t.theme_name,
                action=f"Investigate and resolve user-reported issues related to: {t.theme_name}",
            ))

    return actions[:3]
