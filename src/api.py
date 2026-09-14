from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import asyncio
from pathlib import Path
from typing import Optional

app = FastAPI(title="Groww Review Agent API")

# Allow CORS for all domains for development, restrict in production as needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
PULSES_DIR = BASE_DIR / "data" / "pulses"

class PulseMeta(BaseModel):
    id: str
    label: str
    review_count: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class RefreshResponse(BaseModel):
    success: bool
    error: str | None = None

def _parse_front_matter(content: str) -> dict:
    """Parse YAML front-matter block from a pulse .md file."""
    match = re.match(r'^---\r?\n([\s\S]*?)\r?\n---\r?\n', content)
    if not match:
        return {}
    meta = {}
    for line in match.group(1).splitlines():
        if ':' in line:
            key, _, val = line.partition(':')
            val = val.strip()
            meta[key.strip()] = int(val) if val.isdigit() else val
    return meta

def _fmt_date(iso: str) -> str:
    """Format YYYY-MM-DD as 'Sep 7, 2026'."""
    from datetime import datetime
    try:
        return datetime.strptime(iso, '%Y-%m-%d').strftime('%b %-d, %Y')
    except Exception:
        return iso

@app.get("/api/pulses")
def list_pulses():
    if not PULSES_DIR.exists():
        return {"pulses": []}

    pulses: list[dict] = []
    for f in sorted(PULSES_DIR.iterdir(), reverse=True):
        if not (f.is_file() and f.suffix == '.md'):
            continue
        date_id = f.stem  # e.g. '2026-09-14'
        try:
            content = f.read_text(encoding='utf-8')
            meta = _parse_front_matter(content)
            start_date = meta.get('start_date', '')
            end_date = meta.get('end_date', date_id)
            review_count = int(meta.get('review_count', 0))
            if start_date and end_date:
                label = f"{_fmt_date(start_date)} – {_fmt_date(end_date)}"
            else:
                label = date_id
        except Exception:
            label = date_id
            start_date = ''
            end_date = date_id
            review_count = 0
        pulses.append({
            'id': date_id,
            'label': label,
            'review_count': review_count,
            'start_date': start_date,
            'end_date': end_date,
        })
    return {"pulses": pulses}

@app.get("/api/pulses/{date_str}")
def get_pulse(date_str: str):
    file_path = PULSES_DIR / f"{date_str}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Pulse not found")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return {"content": f.read()}

@app.post("/api/refresh", response_model=RefreshResponse)
async def refresh_analysis():
    try:
        # Run analysis
        proc1 = await asyncio.create_subprocess_exec(
            "python", "-m", "src.main", "--step", "analyze",
            cwd=str(BASE_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout1, stderr1 = await proc1.communicate()
        if proc1.returncode != 0:
            return RefreshResponse(success=False, error=f"Analyze failed: {stderr1.decode()}")

        # Run generate
        proc2 = await asyncio.create_subprocess_exec(
            "python", "-m", "src.main", "--step", "generate",
            cwd=str(BASE_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout2, stderr2 = await proc2.communicate()
        if proc2.returncode != 0:
            return RefreshResponse(success=False, error=f"Generate failed: {stderr2.decode()}")

        return RefreshResponse(success=True)
    except Exception as e:
        return RefreshResponse(success=False, error=str(e))
