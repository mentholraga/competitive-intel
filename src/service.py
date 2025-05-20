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
    If the model emitted extra text around the JSON, 
    pull out the first {...} block for safe parsing.
    """
    match = re.search(r"\{.*\}", s, re.DOTALL)
    return match.group(0) if match else s


def get_checklist(name: str) -> Dict[str, Any]:
    """
    Fetch raw string from GPT, clean it, and return the
    Competitive → intel → checklist dict.
    """
    raw = fetch_intel(name)
    cleaned = clean_json_string(raw)
    json_str = extract_json_object(cleaned)
    parsed = json.loads(json_str)
    # Navigate into the checklist
    return parsed["Competitive"]["intel"]["checklist"]


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/ping")
async def ping():
    return {"ping": "pong"}


@app.post("/fetch-intel", response_model=IntelResponse)
async def fetch_intel_endpoint(req: IntelRequest):
    try:
        raw = fetch_intel(req.company)
        cleaned = clean_json_string(raw)
        parsed = json.loads(extract_json_object(cleaned))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"data": parsed}


@app.post("/export-excel")
async def export_excel_endpoint(req: CompareRequest = Body(...)):
    """
    Expects: { "company1": "NameA", "company2": "NameB" }
    Returns: an .xlsx file with columns [Field, NameA, NameB].
    """
    try:
        chk1 = get_checklist(req.company1)
        chk2 = get_checklist(req.company2)

        # Build row list
        rows = []
        for field, val1 in chk1.items():
            val2 = chk2.get(field, "")
            rows.append({
                "Field": field,
                req.company1: val1,
                req.company2: val2,
            })

        # Write to Excel
        df = pd.DataFrame(rows)
        os.makedirs("data", exist_ok=True)
        out_path = f"data/compare_{req.company1}_vs_{req.company2}.xlsx"
        df.to_excel(out_path, index=False)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return FileResponse(
        out_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(out_path),
    )
