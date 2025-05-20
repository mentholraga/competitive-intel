# src/populate_docx_compare.py

import json
import re
import sys
from docxtpl import DocxTemplate

def sanitize(name: str) -> str:
    """
    Lowercase, replace non-alphanumeric with underscores,
    collapse underscores, strip leading/trailing.
    e.g. "Target Customers" -> "target_customers"
    """
    s = name.lower()
    s = re.sub(r"[^a-z0-9]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def load_checklist(json_path: str) -> dict:
    """
    Load the JSON and return the checklist dict under 
    ["Competitive"]["intel"]["checklist"].
    """
    with open(json_path, "r") as f:
        full = json.load(f)
    try:
        return full["Competitive"]["intel"]["checklist"]
    except (KeyError, TypeError):
        raise RuntimeError(f"Could not find checklist in {json_path}")

def populate_compare(company1: str, company2: str):
    # 1) Load each company's checklist
    data1 = load_checklist(f"data/output_{company1}.json")
    data2 = load_checklist(f"data/output_{company2}.json")

    # 2) Build the template context
    context = {
        "company1_name": company1,
        "company2_name": company2,
    }

    # 3) Map each field in the checklist
    for field, val in data1.items():
        key = sanitize(field)
        context[f"company1_{key}"] = val

    for field, val in data2.items():
        key = sanitize(field)
        context[f"company2_{key}"] = val

    # 4) (Optional) Debug print to verify your keys
    print("❗️ Context keys:")
    for k in sorted(context.keys()):
        print("   ", k)

    # 5) Render your Word template
    tpl = DocxTemplate("data/template.docx")
    tpl.render(context)

    # 6) Save the populated comparison document
    out_path = f"data/final_{company1}_vs_{company2}.docx"
    tpl.save(out_path)
    print(f"✅ Wrote comparison document to {out_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m src.populate_docx_compare <company1> <company2>")
        sys.exit(1)
    populate_compare(sys.argv[1], sys.argv[2])
