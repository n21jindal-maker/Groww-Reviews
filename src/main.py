import argparse
import sys
import json
import datetime
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Groww Review Agent")
    parser.add_argument("--step", choices=["ingest", "analyze", "generate", "deliver"], help="Step to run")
    parser.add_argument("--dry-run", action="store_true", help="Print pulse to console without delivery")
    args = parser.parse_args()

    if args.step == "ingest":
        print("Running ingestion step...")
        from src.ingestion.scraper import fetch_reviews
        from src.ingestion.preprocessor import preprocess
        from src.storage.store import save_reviews, get_review_ids
        
        # Scrape
        raw_reviews = fetch_reviews("com.nextbillion.groww", count=60)
        print(f"Scraped {len(raw_reviews)} reviews.")
        
        # Preprocess
        existing_ids = get_review_ids()
        clean_reviews_data = preprocess(raw_reviews, existing_ids)
        print(f"After PII stripping and dedup, {len(clean_reviews_data)} new reviews to save.")
        
        # Save
        if clean_reviews_data:
            from src.models import Review
            try:
                clean_reviews = [Review(**r) for r in clean_reviews_data]
                save_reviews(clean_reviews)
                print("Ingestion complete. Saved to disk.")
            except Exception as e:
                print(f"Error parsing reviews to Pydantic: {e}")
        else:
            print("No new reviews to save.")
        
    elif args.step == "analyze":
        print("Running analysis step...")
        from src.storage.store import load_reviews
        from src.analysis.chains import analyze_themes, select_quotes, generate_action_ideas
        
        # 1. Load reviews (default last 12 weeks per Phase 2 spec)
        reviews = load_reviews(weeks_ago=12)
        if not reviews:
            print("No reviews found. Please run ingest first.")
            sys.exit(1)
            
        # Use 150 reviews as per current run configuration
        reviews = reviews[:150]
        print(f"Loaded {len(reviews)} reviews for analysis.")
        
        # 2. Analyze themes (batched)
        print("Extracting themes...")
        themes_result = analyze_themes(reviews)
        
        # 3. Select quotes
        print("Selecting quotes...")
        quotes = select_quotes(themes_result, reviews)
        
        # 4. Generate action ideas
        print("Generating action ideas...")
        actions = generate_action_ideas(themes_result)
        
        # 5. Save results to data/analysis/YYYY-MM-DD.json
        base_dir = Path(__file__).resolve().parent.parent
        analysis_dir = base_dir / "data" / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        file_path = analysis_dir / f"{date_str}.json"
        
        analysis_data = {
            "themes": [t.model_dump() for t in themes_result.themes],
            "quotes": quotes,
            "actions": [a.model_dump() for a in actions]
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
        print(f"Analysis saved to {file_path}")

    elif args.step == "generate":
        print("Running generate step...")
        from src.generation.pulse_builder import build_pulse
        from src.storage.store import save_pulse
        from src.models import ClusteringResult, ThemeAssignment, ActionIdea
        
        base_dir = Path(__file__).resolve().parent.parent
        analysis_dir = base_dir / "data" / "analysis"
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        file_path = analysis_dir / f"{date_str}.json"
        
        if not file_path.exists():
            print(f"No analysis found for {date_str}. Please run analyze first.")
            sys.exit(1)
            
        with open(file_path, "r", encoding="utf-8") as f:
            analysis_data = json.load(f)
            
        themes = ClusteringResult(themes=[ThemeAssignment(**t) for t in analysis_data["themes"]])
        quotes = analysis_data["quotes"]
        actions = [ActionIdea(**a) for a in analysis_data["actions"]]
        
        # Calculate dates and counts
        # (Assuming these will be properly loaded from reviews in a robust implementation)
        # For now, we'll pass dummy or estimated values
        review_count = len(quotes) * 100 # Rough estimate if we don't load all reviews
        start_date = (datetime.datetime.now() - datetime.timedelta(weeks=12)).strftime("%b %d, %Y")
        end_date = datetime.datetime.now().strftime("%b %d, %Y")
        
        pulse_md, pulse_text = build_pulse(
            themes=themes,
            quotes=quotes,
            actions=actions,
            review_count=sum(t.count for t in themes.themes),  # actual count from analysis
            start_date=start_date,
            end_date=end_date
        )
        
        if args.dry_run:
            # Reconfigure stdout for UTF-8 so emoji in pulse don't crash on Windows
            import sys, io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            print("\n--- PULSE (MARKDOWN) ---\n")
            print(pulse_md)
            print("\n--- PULSE (PLAIN TEXT) ---\n")
            print(pulse_text)
        else:
            save_pulse(pulse_md, date_str)
            print(f"Pulse generated and saved to data/pulses/{date_str}.md")

    elif args.step == "deliver":
        print("Running deliver step...")
        import asyncio
        from src.agent import run_delivery_agent
        from src.config import config
        
        base_dir = Path(__file__).resolve().parent.parent
        pulses_dir = base_dir / "data" / "pulses"
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        file_path = pulses_dir / f"{date_str}.md"
        
        if not file_path.exists():
            print(f"No pulse found for {date_str}. Please run generate first.")
            sys.exit(1)
            
        with open(file_path, "r", encoding="utf-8") as f:
            pulse_md = f.read()
            
        asyncio.run(run_delivery_agent(pulse_md, config))
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
