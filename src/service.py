# src/service.py

import os
import re
import json
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd

from src.agent import fetch_intel, clean_json_string

app = FastAPI()

from fastapi.staticfiles import StaticFiles

# Serve files in ./data at URL path /static
app.mount("/static", StaticFiles(directory="data"), name="static")



# ─── Models ────────────────────────────────────────────────────────────────────

class IntelRequest(BaseModel):
    company: str

class IntelResponse(BaseModel):
    data: Any

class CompareRequest(BaseModel):
    company1: str
    company2: str


# ─── Helpers ───────────────────────────────────────────────────────────────────

def extract_json_object(s: str) -> str:
    """
    Find the first “{” and last “}” and return that substring.
    This strips any leading/trailing chatter around the JSON.
    """
    start = s.find("{")
    end   = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        return s[start : end+1]
    return s

def get_checklist(name: str) -> Dict[str, Any]:
    """
    Fetch raw string from GPT, clean it, extract the JSON, parse it,
    and return the Competitive → intel → checklist dict.
    """
    raw = fetch_intel(name)
    cleaned = clean_json_string(raw)
    json_str = extract_json_object(cleaned)

    # 🔥 DEBUG LOGGING: print raw vs cleaned vs json_str
    print(f"\n--- RAW from GPT for {name} ---\n{raw}\n")
    print(f"--- CLEANED for {name} ---\n{cleaned}\n")
    print(f"--- EXTRACTED JSON for {name} ---\n{json_str}\n")

    try:
        parsed = json.loads(json_str)
    except Exception as e:
        # include a bit of context in the error so we can debug
        raise RuntimeError(f"Failed to parse JSON for {name}: {e}")

    try:
        return parsed["Competitive"]["intel"]["checklist"]
    except KeyError:
        raise RuntimeError(f"Checklist key not found in parsed JSON for {name}")


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/ping")
async def ping():
    return {"ping": "pong"}


@app.post("/fetch-intel", response_model=IntelResponse)
async def fetch_intel_endpoint(req: IntelRequest):
    try:
        raw = fetch_intel(req.company)
        cleaned = clean_json_string(raw)
        extracted = extract_json_object(cleaned)
        parsed = json.loads(extracted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"data": parsed}


@app.post("/compare-url")
async def compare_url(req: CompareRequest = Body(...)):
    """
    Generates the XLSX, saves it in ./data, and returns JSON with its public URL.
    """
    try:
        # Generate the file exactly as /export-excel does
        chk1 = get_checklist(req.company1)
        chk2 = get_checklist(req.company2)

        rows = []
        for field, val1 in chk1.items():
            rows.append({
                "Field": field,
                req.company1: val1,
                req.company2: chk2.get(field, ""),
            })

        df = pd.DataFrame(rows)
        os.makedirs("data", exist_ok=True)
        fname = f"compare_{req.company1}_vs_{req.company2}.xlsx"
        out_path = os.path.join("data", fname)
        df.to_excel(out_path, index=False)

        # Build the public URL (note: match your Render domain)
        public_url = f"https://competitive-intel.onrender.com/static/{fname}"
        return {"url": public_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    return FileResponse(
        out_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(out_path),
    )
