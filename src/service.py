# src/service.py

import os
import re
import json
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd

from src.agent import fetch_intel, clean_json_string

app = FastAPI()

# Serve files in ./data at URL path /static
app.mount("/static", StaticFiles(directory="data"), name="static")


def flatten_dict(d: Dict[Any, Any], parent_key: str = "", sep: str = " — ") -> Dict[str, Any]:
    """
    Recursively flatten nested dicts so every leaf value
    gets its own flat key, e.g. "Category — Subkey".
    """
    items: Dict[str, Any] = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key, sep=sep))
        else:
            items[new_key] = v
    return items


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
    """Extract the JSON object between the first '{' and its matching '}'."""
    start = s.find("{")
    if start == -1:
        return s
    depth = 0
    for i, ch in enumerate(s[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return s


def get_checklist(name: str) -> Dict[str, Any]:
    """
    Fetch raw GPT output, clean and parse it, then return the
    'checklist' dict from either shape of JSON.
    """
    raw = fetch_intel(name)
    cleaned = clean_json_string(raw)
    json_str = extract_json_object(cleaned)

    # Fix broken two‐key patterns like `"last": "reviewed": "…"`
    json_str = re.sub(
        r'"([^"]+)":\s*"([^"]+)":\s*"([^"]+)"',
        r'"\1 \2": "\3"',
        json_str
    )
    # Strip trailing commas before closing } or ]
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

    # Debug logs
    print(f"\n--- RAW from GPT for {name} ---\n{raw}\n")
    print(f"--- CLEANED for {name} ---\n{cleaned}\n")
    print(f"--- EXTRACTED JSON for {name} ---\n{json_str}\n")

    try:
        parsed = json.loads(json_str)
    except Exception as e:
        raise RuntimeError(f"Failed to parse JSON for {name}: {e}")

    # Support either {"Competitive": { "intel": {...} }} or { "intel": {...} }
    if isinstance(parsed.get("Competitive"), dict):
        intel = parsed["Competitive"].get("intel", {})
    elif isinstance(parsed.get("intel"), dict):
        intel = parsed["intel"]
    else:
        raise RuntimeError(f"Cannot find intel section in parsed JSON for {name}")

    checklist = intel.get("checklist", {})
    if not isinstance(checklist, dict):
        raise RuntimeError(f"Checklist for {name} is not an object")
    return checklist


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
        # Also strip trailing commas just in case
        extracted = re.sub(r',\s*([}\]])', r'\1', extracted)
        parsed = json.loads(extracted)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"data": parsed}


@app.post("/compare-url")
async def compare_url(req: CompareRequest = Body(...)):
    try:
        # 1) Get and flatten both checklists
        chk1_raw = get_checklist(req.company1)
        chk2_raw = get_checklist(req.company2)
        flat1 = flatten_dict(chk1_raw)
        flat2 = flatten_dict(chk2_raw)

        # 2) Load the master field list
        with open("data/schema.json") as f:
            schema = json.load(f)
        all_fields = [f["name"] for f in schema["fields"]]

        # 3) Ensure no field is missing
        for field in all_fields:
            flat1.setdefault(field, "Not available")
            flat2.setdefault(field, "Not available")

        # 4) Build rows in schema order
        rows = []
        for field in all_fields:
            rows.append({
                "Field":       field,
                req.company1:  flat1[field],
                req.company2:  flat2[field],
            })

        # 5) Write to Excel
        df = pd.DataFrame(rows)
        os.makedirs("data", exist_ok=True)
        fname = f"compare_{req.company1}_vs_{req.company2}.xlsx"
        out_path = os.path.join("data", fname)
        df.to_excel(out_path, index=False)

        # 6) Return the public URL
        return {"url": f"https://competitive-intel.onrender.com/static/{fname}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
