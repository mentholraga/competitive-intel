# src/service.py

import os
import json
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Any
import pandas as pd

from src.agent import fetch_intel, clean_json_string

app = FastAPI()

class IntelRequest(BaseModel):
    company: str

class IntelResponse(BaseModel):
    data: Any

@app.get("/ping")
async def ping():
    return {"ping": "pong"}

@app.post("/fetch-intel", response_model=IntelResponse)
async def fetch_intel_endpoint(req: IntelRequest):
    try:
        raw = fetch_intel(req.company)
        cleaned = clean_json_string(raw)
        parsed = json.loads(cleaned)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"data": parsed}


class CompareRequest(BaseModel):
    company1: str
    company2: str

@app.post("/export-excel")
async def export_excel_endpoint(req: CompareRequest = Body(...)):
    """
    Expects JSON {"company1":"NameA","company2":"NameB"}.
    Returns an XLSX file comparing their intel side by side.
    """
    try:
        # Fetch & parse both companies
        def get_checklist(name: str):
            raw = fetch_intel(name)
            cleaned = clean_json_string(raw)
            parsed = json.loads(cleaned)
            # Drill into the checklist
            return parsed["Competitive"]["intel"]["checklist"]

        chk1 = get_checklist(req.company1)
        chk2 = get_checklist(req.company2)

        # Build rows for Excel
        rows = []
        for field, val1 in chk1.items():
            val2 = chk2.get(field, "")
            rows.append({
                "Field": field,
                req.company1: val1,
                req.company2: val2
            })

        # Create DataFrame and write to disk
        df = pd.DataFrame(rows)
        out_path = f"data/compare_{req.company1}_vs_{req.company2}.xlsx"
        # ensure data/ exists
        os.makedirs("data", exist_ok=True)
        df.to_excel(out_path, index=False)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return FileResponse(
        out_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(out_path),
    )
