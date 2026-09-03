# Groww Review Agent — Edge Cases & Failure Scenarios

This document catalogs edge cases, boundary conditions, and failure scenarios across every layer of the Groww Review Agent pipeline. Each entry includes the scenario, expected behavior, and recommended handling strategy.

---

## 1. Review Ingestion Edge Cases

### 1.1 Zero Reviews Fetched

| Aspect | Detail |
|---|---|
| **Scenario** | `google-play-scraper` returns an empty list — no reviews available for the configured time window (e.g., new app listing, API outage, regional restriction). |
| **Impact** | Entire pipeline has nothing to process. |
| **Handling** | Log a clear warning: `"No reviews found for com.nextbillion.groww in the last {N} weeks"`. Skip analysis and generation. Do NOT publish an empty pulse or create an empty Gmail draft. Exit with code 0 (not an error). |

### 1.2 Very Few Reviews (<10)

| Aspect | Detail |
|---|---|
| **Scenario** | Only 3–9 reviews fetched. Too few to produce meaningful theme clusters. |
| **Impact** | Theme clustering may produce noisy or single-review "themes." Quotes may not be representative. |
| **Handling** | Set a configurable `MIN_REVIEWS_THRESHOLD` (default: 10). If below threshold, log warning and either (a) skip pulse generation, or (b) generate a simplified pulse noting "insufficient data for full analysis." Include all reviews verbatim instead of clustering. |

### 1.3 Extremely High Review Volume (>5,000)

| Aspect | Detail |
|---|---|
| **Scenario** | A viral event or app update triggers thousands of reviews in the ingestion window. |
| **Impact** | Gemini token limits may be exceeded. `google-play-scraper` may time out or rate-limit. JSON storage files become unwieldy. |
| **Handling** | Batch scraping with configurable `MAX_REVIEWS_PER_FETCH` (default: 1000). For LLM clustering, sample a representative subset (stratified by rating) rather than sending all reviews. Process in batches of 50–100 for the theme chain. |

### 1.4 Duplicate Reviews Across Runs

| Aspect | Detail |
|---|---|
| **Scenario** | Running ingestion twice on the same day (or overlapping windows) produces duplicate review entries. |
| **Impact** | Inflated theme counts, duplicate quotes, skewed analysis. |
| **Handling** | Deduplicate by `review_id` before storage. `store.get_review_ids()` returns existing IDs; skip any review whose ID is already present. Log count of skipped duplicates. |

### 1.5 Reviews in Non-English Languages

| Aspect | Detail |
|---|---|
| **Scenario** | Groww serves Indian users — reviews may be in Hindi, Tamil, Telugu, Marathi, Bengali, or transliterated Hinglish (e.g., "KYC bahut slow hai"). |
| **Impact** | LLM clustering may miscategorize non-English reviews. Quotes in unfamiliar scripts may confuse stakeholders. |
| **Handling** | Option A (MVP): Filter to English-only reviews using the `lang` field from `google-play-scraper`. Option B (enhanced): Pass all reviews to Gemini which handles multilingual input natively. Flag non-English quotes in the pulse with `[translated]` annotation. |

### 1.6 Reviews With Only Rating, No Text

| Aspect | Detail |
|---|---|
| **Scenario** | Users submit star ratings without any text content (e.g., `{"rating": 1, "text": "", "date": "..."}`). |
| **Impact** | Empty text cannot be clustered or quoted. Inflates review count without adding analytical value. |
| **Handling** | Filter out reviews where `text` is `null`, empty, or whitespace-only during preprocessing. Log: `"Filtered {N} text-less reviews (rating-only)."` Still count them in overall metrics (e.g., average rating). |

### 1.7 Scraper Library Breaking Change

| Aspect | Detail |
|---|---|
| **Scenario** | `google-play-scraper` stops working because Google changes the Play Store's HTML/API structure. The library returns errors or malformed data. |
| **Impact** | Complete ingestion failure. No new reviews can be fetched. |
| **Handling** | Wrap scraper calls in try/except. If scraper fails, fall back to cached reviews from the most recent successful run. Log a critical alert: `"Scraper failure — using cached reviews from {date}"`. Provide a manual CSV import option (`--import-csv reviews.csv`) as an emergency bypass. |

### 1.8 Rate Limiting by Play Store

| Aspect | Detail |
|---|---|
| **Scenario** | Too many requests in a short period trigger HTTP 429 or connection resets from Google Play. |
| **Impact** | Partial data — only some reviews fetched before the block. |
| **Handling** | Implement exponential backoff with jitter (3 retries, starting at 2s). Add a configurable `REQUEST_DELAY_MS` between pagination calls (default: 500ms). If all retries fail, proceed with whatever reviews were fetched (if any), or use cache. |

---

## 2. PII & Privacy Edge Cases

### 2.1 PII Embedded in Review Text

| Aspect | Detail |
|---|---|
| **Scenario** | A user writes: `"Contact me at john.doe@gmail.com, my phone is +91-9876543210, reference ID ABC123DEF456"`. |
| **Impact** | PII leaks into stored data, LLM prompts, Google Docs, and Gmail drafts. |
| **Handling** | Regex-based PII stripper runs **before** storage. Replace: emails → `[email]`, phones → `[phone]`, long alphanumeric IDs → `[id]`. Defense-in-depth: run PII scanner again at pulse generation. |

### 2.2 PII in Non-Standard Formats

| Aspect | Detail |
|---|---|
| **Scenario** | PII written in non-standard formats: `"mail me at john dot doe at gmail dot com"`, `"my number is nine eight seven six..."`, or `"UPI ID: user@oksbi"`. |
| **Impact** | Regex patterns miss these. PII leaks through. |
| **Handling** | Add heuristic patterns for common obfuscation. Consider an LLM-based PII detection pass as a secondary check (ask Gemini: "Does this text contain any personally identifiable information?"). Flag uncertain cases for manual review. |

### 2.3 Reviewer Usernames in Review Metadata

| Aspect | Detail |
|---|---|
| **Scenario** | `google-play-scraper` returns `userName` field with each review (e.g., `"Rahul Sharma"`). |
| **Impact** | If stored or sent to LLM, this is PII. |
| **Handling** | Strip `userName`, `userImage`, and any other user-identifying metadata fields during preprocessing. Only retain: `reviewId`, `score`, `text`, `at`, `appVersion`. Define an explicit allowlist of safe fields. |

### 2.4 PII in Selected Quotes

| Aspect | Detail |
|---|---|
| **Scenario** | The quote selection chain picks a review that still contains subtle PII after stripping (e.g., a unique transaction ID or a location-specific complaint that identifies the user). |
| **Impact** | PII published in the Google Doc and Gmail draft. |
| **Handling** | Add a post-selection PII scan on the 3 chosen quotes. If any PII detected, either redact and use, or ask the LLM to pick an alternative quote from the same theme. |

---

## 3. LangChain Analysis Edge Cases

### 3.1 LLM Returns More Than 5 Themes

| Aspect | Detail |
|---|---|
| **Scenario** | Despite the prompt saying "at most 5 themes," Gemini returns 6 or 7 theme clusters. |
| **Impact** | Violates the max-5-themes constraint. Pydantic validation may fail if `max_length=5` is enforced. |
| **Handling** | `PydanticOutputParser` with `max_length=5` on the themes list will raise a `ValidationError`. Catch this and either: (a) truncate to top 5 by count, or (b) re-prompt with stricter instruction. Use `OutputFixingParser` for automatic correction. |

### 3.2 LLM Returns Fewer Than 3 Themes

| Aspect | Detail |
|---|---|
| **Scenario** | All reviews cluster into 1 or 2 themes (e.g., a major outage where everyone complains about the same thing). |
| **Impact** | Pulse expects "top 3 themes" but only 1–2 exist. Quote and action chains expect 3 themes. |
| **Handling** | If fewer than 3 themes, adjust the pulse to show only the available themes. Modify the pulse template dynamically: `"Top {N} Themes"`. Still generate 3 action ideas by asking for multiple actions per theme. |

### 3.3 LLM Invents Fake Quotes

| Aspect | Detail |
|---|---|
| **Scenario** | The quote selection chain generates a quote that sounds real but doesn't match any stored review verbatim. |
| **Impact** | Violates the "no invented wording" requirement. Stakeholders may make decisions based on fabricated feedback. |
| **Handling** | **Post-generation validation:** Compare each selected quote against the stored review corpus using fuzzy matching (e.g., `fuzz.ratio` > 85%). If a quote doesn't match any real review, reject it and ask the chain to re-select. Alternatively, pre-filter candidate quotes in Python and ask the LLM to rank/pick from the filtered list instead of generating freely. |

### 3.4 LLM Output Fails to Parse (Malformed JSON)

| Aspect | Detail |
|---|---|
| **Scenario** | Gemini returns JSON with syntax errors, missing fields, or unexpected structure that `PydanticOutputParser` cannot parse. |
| **Impact** | Chain throws `OutputParserException`. Pipeline halts. |
| **Handling** | Use `OutputFixingParser` which auto-retries by sending the malformed output + error message back to the LLM with a correction prompt. Set `max_retries=2`. If still failing, fall back to `JsonOutputParser` with manual field extraction. Log the raw response for debugging. |

### 3.5 Token Limit Exceeded

| Aspect | Detail |
|---|---|
| **Scenario** | Sending all 500+ reviews in a single prompt exceeds Gemini's context window (e.g., 1M tokens for Flash, but very long prompts increase cost and latency). |
| **Impact** | API error or truncated response. Themes based on partial data. |
| **Handling** | Implement a `MAX_REVIEWS_PER_PROMPT` limit (default: 100). If more reviews exist, use a map-reduce pattern: cluster batches of 100 → merge sub-clusters into final ≤ 5 themes. Alternatively, send only review text (not full metadata) to minimize tokens. |

### 3.6 Inconsistent Theme Labels Across Runs

| Aspect | Detail |
|---|---|
| **Scenario** | Week 1 produces theme "KYC Problems", Week 2 produces "KYC Verification Issues" for the same topic. |
| **Impact** | Stakeholders can't track themes over time. Historical comparison is impossible. |
| **Handling** | Seed the clustering prompt with a predefined list of suggested theme categories: `["Onboarding/KYC", "Payments", "App Performance", "Customer Support", "Withdrawals/Refunds"]`. Instruct the LLM to map to these categories when possible and only create new labels for genuinely new themes. Use low temperature (0.3). |

### 3.7 All Reviews Are Positive (or All Negative)

| Aspect | Detail |
|---|---|
| **Scenario** | During a period of high satisfaction (or a major outage), all reviews skew heavily to 4–5 stars (or 1–2 stars). |
| **Impact** | Themes may all be positive ("Great app!", "Love it!") with no actionable insights. Or all negative with no differentiation. |
| **Handling** | Detect skew: if >90% of reviews are the same sentiment, add a note to the pulse: `"Note: This week's reviews are overwhelmingly {positive/negative}."` For all-positive: still surface improvement themes from the minority negative reviews. For all-negative: prioritize by severity/frequency. |

### 3.8 Gemini API Outage or Quota Exhaustion

| Aspect | Detail |
|---|---|
| **Scenario** | Gemini API returns 503/429 errors for an extended period, or the daily quota is exhausted mid-pipeline. |
| **Impact** | Analysis chains cannot complete. No themes, quotes, or actions generated. |
| **Handling** | LangChain `.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)`. If all retries fail: check for cached analysis results from the previous run. If available, re-use last week's themes and generate a "partial update" pulse. Log critical alert. |

---

## 4. Pulse Generation Edge Cases

### 4.1 Pulse Exceeds 250-Word Limit

| Aspect | Detail |
|---|---|
| **Scenario** | The assembled pulse (themes + quotes + actions) exceeds 250 words, especially with long quotes or verbose action ideas. |
| **Impact** | Violates the ≤ 250-word constraint. Note becomes harder to scan. |
| **Handling** | Post-generation word count check. If over limit: (a) re-prompt the LLM with: `"Condense this pulse to under 250 words while preserving all key information."` (b) If still over after 2 attempts, truncate action ideas to 1 sentence each and trim quotes. Log warning. |

### 4.2 Quotes Contain Special Characters or Markdown Syntax

| Aspect | Detail |
|---|---|
| **Scenario** | A verbatim quote contains characters that break Markdown rendering: `"App shows **error** and #crash every time!!"` or backticks, pipes, etc. |
| **Impact** | Google Docs formatting breaks. Markdown artifacts render incorrectly. |
| **Handling** | Escape Markdown special characters in quotes before template insertion. Preserve the verbatim text but wrap in code-style formatting if needed. For Google Docs (which uses HTML/plain text), strip Markdown syntax from quotes. |

### 4.3 Theme Counts Don't Sum to Total Reviews

| Aspect | Detail |
|---|---|
| **Scenario** | Due to LLM clustering, some reviews are assigned to no theme (orphaned) or assigned to multiple themes (duplicated). |
| **Impact** | Summary stats are misleading. "412 reviews analyzed" but theme counts sum to 380 or 450. |
| **Handling** | Post-clustering validation: check that every review_id appears in exactly one theme. Orphaned reviews → assign to an "Other" bucket. Duplicates → assign to the first matching theme only. Log discrepancies. |

### 4.4 Empty or Null Fields in Analysis Output

| Aspect | Detail |
|---|---|
| **Scenario** | LLM returns a theme with `theme_name: ""` or an action idea that's `null`. |
| **Impact** | Pulse template renders blanks or crashes on `None` access. |
| **Handling** | Pydantic validators with `min_length=1` on string fields. Add a `@field_validator` that strips whitespace and rejects empty strings. If any field is empty after parsing, re-invoke the chain for that specific output. |

### 4.5 Date Range Ambiguity in Pulse Header

| Aspect | Detail |
|---|---|
| **Scenario** | Reviews span an irregular date range (e.g., some from 12 weeks ago, some from yesterday) making "Week of {date}" misleading. |
| **Impact** | Stakeholders may misinterpret the time period covered. |
| **Handling** | Calculate the actual date range from the reviews: `min(review.date)` to `max(review.date)`. Display as: `"Period: Jun 23 – Sep 01, 2026"` instead of a single week date. Include total review count. |

---

## 5. MCP Delivery Edge Cases

### 5.1 MCP Server Not Installed or Not Found

| Aspect | Detail |
|---|---|
| **Scenario** | The `npx` command for the MCP server fails because Node.js is not installed, the package doesn't exist, or `npx` is not in PATH. |
| **Impact** | Delivery completely fails. No Google Doc or Gmail draft created. |
| **Handling** | Pre-flight check at pipeline start: verify `npx --version` succeeds. If not, log error with installation instructions and skip delivery. Save pulse to `data/pulses/` as fallback. Print: `"Pulse saved locally. Install Node.js and MCP servers to enable delivery."` |

### 5.2 Google OAuth Credentials Expired or Invalid

| Aspect | Detail |
|---|---|
| **Scenario** | The Google credentials JSON at `config/google-credentials.json` has expired tokens, wrong scopes, or is missing entirely. |
| **Impact** | MCP servers fail to authenticate. 401/403 errors. |
| **Handling** | Catch authentication errors from MCP tool calls. Log: `"Google credentials error — re-authenticate using OAuth flow."` Provide a link or command to refresh credentials. Save pulse locally as fallback. |

### 5.3 Google Docs Creation Fails Mid-Write

| Aspect | Detail |
|---|---|
| **Scenario** | The `create_document` MCP tool call starts but fails partway (network drop, API error). A partial or empty Doc may be created. |
| **Impact** | Orphaned Google Doc with incomplete content. Gmail draft may reference a broken Doc URL. |
| **Handling** | After `create_document`, immediately call `get_document` to verify the content was written correctly. If verification fails, delete the partial Doc and retry once. If retry fails, save locally and skip Gmail draft. |

### 5.4 Gmail Draft Creation Fails After Doc Succeeds

| Aspect | Detail |
|---|---|
| **Scenario** | Google Doc is created successfully, but the Gmail `create_draft` call fails. |
| **Impact** | Doc exists but no one is notified. The pipeline reports partial success. |
| **Handling** | Log the Doc URL so it's not lost: `"Doc created at {url} but Gmail draft failed."` Retry Gmail draft once. If still failing, print the Doc URL and email content to console so the user can manually send it. |

### 5.5 Duplicate Google Docs on Re-Run

| Aspect | Detail |
|---|---|
| **Scenario** | Running the pipeline twice in the same week creates two separate Google Docs with the same content. |
| **Impact** | Stakeholders confused by duplicate documents. Storage clutter. |
| **Handling** | Check if a pulse for the current week already exists (by title pattern or stored doc_id). If yes, use `update_document` instead of `create_document`. Store the `doc_id` in `data/pulses/` metadata for idempotent updates. |

### 5.6 Email Recipient Address Invalid

| Aspect | Detail |
|---|---|
| **Scenario** | `config.yaml` contains a typo in the `email.to` field (e.g., `"user@gmial.com"` or `""`). |
| **Impact** | Gmail draft created but will bounce on send. Or MCP tool rejects the invalid address. |
| **Handling** | Validate email format at config load time with a regex check. Reject empty or malformed addresses before reaching the delivery stage. Log: `"Invalid email address in config: {address}. Skipping Gmail draft."` |

---

## 6. Data Storage Edge Cases

### 6.1 Disk Full / Write Permission Denied

| Aspect | Detail |
|---|---|
| **Scenario** | The `data/reviews/` or `data/pulses/` directory cannot be written to (permissions issue, disk full, read-only filesystem). |
| **Impact** | Reviews and pulses cannot be persisted. Pipeline may crash. |
| **Handling** | Wrap all file writes in try/except. If write fails, log the error and continue with in-memory data. At least complete the current pipeline run even if persistence fails. Alert: `"WARNING: Could not save to disk. Data will be lost after this run."` |

### 6.2 Corrupted JSON Files

| Aspect | Detail |
|---|---|
| **Scenario** | A previous crash left a `data/reviews/2026-09-01.json` file with truncated or invalid JSON. |
| **Impact** | `json.load()` throws `JSONDecodeError`. Pipeline cannot load historical reviews. |
| **Handling** | Wrap JSON loading in try/except. If a file is corrupted, log a warning and skip it. Attempt to load remaining files. Consider writing JSON with `.tmp` → rename pattern (atomic writes) to prevent future corruption. |

### 6.3 Very Large JSON Files (>100MB)

| Aspect | Detail |
|---|---|
| **Scenario** | Months of accumulated reviews in a single JSON file become too large to load into memory. |
| **Impact** | `MemoryError` or extreme slowness. |
| **Handling** | Partition reviews by date: one JSON file per ingestion batch (`YYYY-MM-DD.json`). When loading for analysis, only load files within the configured `review_window_weeks`. Add a config option `max_file_size_mb` with a warning if exceeded. |

---

## 7. Configuration & Environment Edge Cases

### 7.1 Missing or Empty `.env` File

| Aspect | Detail |
|---|---|
| **Scenario** | User clones the repo but forgets to create `.env` from `.env.example`. `GOOGLE_API_KEY` is unset. |
| **Impact** | LangChain `ChatGoogleGenerativeAI` throws `ValueError` on initialization. |
| **Handling** | Check for required environment variables at startup. If missing, print a clear error: `"Missing GOOGLE_API_KEY. Copy .env.example to .env and fill in your API key."` Exit with code 1. Do not proceed with empty/null keys. |

### 7.2 Invalid `config.yaml` Values

| Aspect | Detail |
|---|---|
| **Scenario** | User sets `max_themes: 0`, `review_window_weeks: -1`, or `max_pulse_words: 10000`. |
| **Impact** | Unexpected behavior — zero themes requested, negative date ranges, or unbounded pulse length. |
| **Handling** | Validate all config values at load time with Pydantic `BaseSettings` or manual checks. Enforce bounds: `max_themes: 1–10`, `review_window_weeks: 1–52`, `max_pulse_words: 50–500`. Reject invalid configs with descriptive error messages. |

### 7.3 Wrong App ID in Config

| Aspect | Detail |
|---|---|
| **Scenario** | `play_store_app_id` is set to a non-existent app ID or a different app entirely. |
| **Impact** | Fetching reviews for the wrong app, or getting an empty result / error from `google-play-scraper`. |
| **Handling** | On first run, log the app name returned by the scraper and ask for confirmation: `"Fetching reviews for: Groww - Stocks, Mutual Funds. Is this correct? (y/n)"`. In non-interactive mode, validate the app ID format (`com.xxx.yyy`). |

---

## 8. Concurrency & Timing Edge Cases

### 8.1 Pipeline Run While Previous Run Is Still Active

| Aspect | Detail |
|---|---|
| **Scenario** | Cron triggers a new pipeline run while the previous one is still processing (e.g., slow LLM responses). |
| **Impact** | Race conditions on JSON file writes. Duplicate Docs/drafts. Inconsistent state. |
| **Handling** | Use a lock file (`data/.pipeline.lock`). At startup, check for lock. If locked, log: `"Pipeline already running. Skipping this invocation."` Remove lock on completion (or after a timeout). |

### 8.2 Clock Skew / Timezone Issues

| Aspect | Detail |
|---|---|
| **Scenario** | Server timezone differs from IST (India Standard Time). Review dates from Play Store are in UTC. Pulse header says "Week of Sep 03" but reviews end on Sep 02. |
| **Impact** | Confusing date ranges in the pulse. Reviews may be incorrectly filtered by date window. |
| **Handling** | Normalize all dates to UTC internally. Convert to IST only for display in the pulse. Use `datetime.timezone.utc` consistently. Document the timezone convention in `config.yaml`. |

---

## Summary Matrix

| Layer | # Edge Cases | Critical Risk Areas |
|---|---|---|
| **Ingestion** | 8 | Scraper failure, rate limiting, non-English reviews |
| **PII / Privacy** | 4 | Non-standard PII formats, metadata leakage |
| **LangChain Analysis** | 8 | Fake quotes, token limits, inconsistent themes |
| **Pulse Generation** | 5 | Word limit, special characters, empty fields |
| **MCP Delivery** | 6 | OAuth expiry, duplicate Docs, partial failures |
| **Data Storage** | 3 | Corrupted JSON, disk full, large files |
| **Config / Environment** | 3 | Missing API keys, invalid config values |
| **Concurrency / Timing** | 2 | Lock file, timezone normalization |
| **Total** | **39** | |

> [!IMPORTANT]
> **Priority edge cases to handle first (highest impact × likelihood):**
> 1. PII leakage (§2) — reputational and legal risk
> 2. LLM invents fake quotes (§3.3) — violates core requirement
> 3. Scraper failure (§1.7) — blocks entire pipeline
> 4. Token limit exceeded (§3.5) — silent data loss
> 5. Missing API keys (§7.1) — poor developer experience
