# src/schema.py

import json
from src.loader import extract_text, extract_fields

def build_schema(pdf_path: str, out_path: str):
    """
    Reads the checklist PDF, extracts field names, 
    and writes a JSON schema to out_path.
    """
    text = extract_text(pdf_path)
    fields = extract_fields(text)
    schema = {
        "fields": [
            {"name": field, "type": "string"}
            for field in fields
        ]
    }
    with open(out_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Wrote schema with {len(fields)} fields to {out_path}")

if __name__ == "__main__":
    build_schema("data/template.pdf", "data/schema.json")

