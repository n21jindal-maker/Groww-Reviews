import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_config():
    """Loads the configuration from config/config.yaml."""
    # Compute base dir (assumes src is a subdirectory of the project root)
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "config" / "config.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    return config

# Load config when module is imported
config = load_config()

# Validate important environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your_gemini_api_key_here":
    import warnings
    warnings.warn("GOOGLE_API_KEY is not set or still uses the default value. Please update your .env file.")
