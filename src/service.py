# src/service.py

import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any
from src.agent import fetch_intel, clean_json_string

app = FastAPI()

class IntelRequest(BaseModel):
    company: str

class IntelResponse(BaseModel):
    data: Any

@app.post("/fetch-intel", response_model=IntelResponse)
async def fetch_intel_endpoint(req: IntelRequest):
    try:
        raw = fetch_intel(req.company)
        cleaned = clean_json_string(raw)
        parsed = json.loads(cleaned)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"data": parsed}
