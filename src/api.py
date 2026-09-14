from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import subprocess
import asyncio
from pathlib import Path

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

class RefreshResponse(BaseModel):
    success: bool
    error: str | None = None

@app.get("/api/pulses")
def list_pulses():
    if not PULSES_DIR.exists():
        return {"pulses": []}
    
    files = []
    for f in PULSES_DIR.iterdir():
        if f.is_file() and f.suffix == ".md":
            files.append(f.name)
            
    # Sort newest first
    files.sort(reverse=True)
    return {"pulses": [f.replace(".md", "") for f in files]}

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
