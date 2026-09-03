import argparse
import sys
from src.config import config

def main():
    parser = argparse.ArgumentParser(description=config['app']['name'])
    parser.add_argument("--step", type=str, choices=["ingest", "analyze", "deliver"], help="Run a specific step of the pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Run the full pipeline but skip delivery")
    
    args = parser.parse_args()

    print(f"Starting {config['app']['name']} pipeline...")
    
    if args.step == "ingest":
        print("Running ingestion step...")
        # TODO: Implement ingestion
    elif args.step == "analyze":
        print("Running analysis step...")
        # TODO: Implement analysis
    elif args.step == "deliver":
        print("Running delivery step...")
        # TODO: Implement delivery
    else:
        print("Running full pipeline...")
        if args.dry_run:
            print("DRY RUN: MCP delivery will be skipped.")
        # TODO: Implement full pipeline flow
        
if __name__ == "__main__":
    main()
