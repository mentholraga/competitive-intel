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
                return s[start : i+1]
    return s

def get_checklist(name: str) -> Dict[str, Any]:
    raw = fetch_intel(name)
    cleaned = clean_json_string(raw)
    json_str = extract_json_object(cleaned)

    # ─── Fix broken two‐key patterns: "last": "reviewed": "01/10/2023"
    json_str = re.sub(
        r'"([^"]+)":\s*"([^"]+)":\s*"([^"]+)"',
        r'"\1 \2": "\3"',
        json_str
    )
    # ─── Strip trailing commas
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

    # DEBUG logs
    print(f"\n--- RAW from GPT for {name} ---\n{raw}\n")
    print(f"--- CLEANED for {name} ---\n{cleaned}\n")
    print(f"--- EXTRACTED JSON for {name} ---\n{json_str}\n")

    try:
        parsed = json.loads(json_str)
    except Exception as e:
        raise RuntimeError(f"Failed to parse JSON for {name}: {e}")

    # ─── Support both JSON shapes ───
    if isinstance(parsed.get("Competitive"), dict):
        intel_section = parsed["Competitive"]["intel"]
    elif isinstance(parsed.get("intel"), dict):
        intel_section = parsed["intel"]
    else:
        raise RuntimeError(f"Cannot find intel section in parsed JSON for {name}")

    checklist = intel_section.get("checklist", {})
    if not isinstance(checklist, dict):
        raise RuntimeError(f"Checklist for {name} is not an object")
    return checklist

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
    try:
        chk1 = get_checklist(req.company1)
        chk2 = get_checklist(req.company2)

        # 🔥 DEBUG: log types & sample
        print(f"--- compare-url DEBUG for {req.company1} → type {type(chk1)}")
        print(chk1)
        print(f"--- compare-url DEBUG for {req.company2} → type {type(chk2)}")
        print(chk2)

        rows = []
        for field, val1 in chk1.items():  # ← error is happening here
            val2 = chk2.get(field, "")
            rows.append({ "Field": field, req.company1: val1, req.company2: val2 })


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
