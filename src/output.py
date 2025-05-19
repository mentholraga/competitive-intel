# src/output.py

import json
import pandas as pd
import sys

def flatten_dict(d: dict, parent_key: str = "") -> dict:
    """
    Recursively flattens a nested dict by joining keys with ' — '.
    E.g. {'A': {'B': 'v'}} → {'A — B': 'v'}.
    """
    items: dict = {}
    for k, v in d.items():
        new_key = f"{parent_key}{k}" if not parent_key else f"{parent_key} — {k}"
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key))
        else:
            items[new_key] = v
    return items

def json_to_dataframe(json_path: str) -> pd.DataFrame:
    """
    Reads the nested output JSON, unwraps its single root,
    flattens all fields, and returns a DataFrame with columns ['Field', 'Value'].
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    # If there's exactly one top‐level key whose value is a dict, unwrap it
    if len(data) == 1 and isinstance(next(iter(data.values())), dict):
        data = next(iter(data.values()))

    flat = flatten_dict(data)
    df = pd.DataFrame(list(flat.items()), columns=["Field", "Value"])
    return df

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.output <company_name>")
        sys.exit(1)

    company = sys.argv[1]
    json_path = f"data/output_{company}.json"

    # Build DataFrame from the nested JSON and flatten it
    df = json_to_dataframe(json_path)

    # Write out new CSV & Excel
    csv_path = f"data/output_{company}.csv"
    excel_path = f"data/output_{company}.xlsx"
    df.to_csv(csv_path, index=False)
    df.to_excel(excel_path, index=False)

    print(f"✅ Wrote CSV to {csv_path}")
    print(f"✅ Wrote Excel to {excel_path}")

if __name__ == "__main__":
    main()
