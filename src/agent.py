# src/agent.py

import json
import sys
from openai import OpenAI
from src.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def clean_json_string(s: str) -> str:
    """
    Strips Markdown fences (```json … ```) if present,
    and returns the inner text.
    """
    s = s.strip()
    # If it starts with a code fence, drop the first line and last fence
    if s.startswith("```"):
        # e.g. ```json\n{...}\n```
        parts = s.split("\n")
        # drop the opening ```whatever and the closing ```
        inner = "\n".join(parts[1:-1])
        return inner.strip()
    return s


def load_schema(path: str) -> dict:
    """Read the JSON schema of fields."""
    with open(path, "r") as f:
        return json.load(f)


def build_prompt(company: str, fields: list[str]) -> str:
    """
    Generate a user prompt that asks for each field, 
    and instructs the model to return only valid JSON.
    """
    prompt = (
        f"You are a competitive intelligence analyst.\n"
        f"For the company \"{company}\", please provide concise, fact-based\n"
        f"answers for each of the following fields. Return ONLY a valid JSON\n"
        f"object, where each key exactly matches the field name.\n\n"
        "Fields:\n"
    )
    for name in fields:
        prompt += f"- {name}\n"
    return prompt


def fetch_intel(company: str, schema_path: str = "data/schema.json") -> str:
    # 2) Load schema and extract field list
    schema = load_schema(schema_path)
    field_names = [f["name"] for f in schema["fields"]]

    # 3) Build the user prompt
    user_prompt = build_prompt(company, field_names)

    # 4) Call the 1.x API
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.2
    )

    # 5) Return the JSON string the model emitted
    return resp.choices[0].message.content


if __name__ == "__main__":
    # 1) Startup notice
    print("🚀 Agent starting up…")

    # 2) Ensure we got a company name
    if len(sys.argv) < 2:
        print("Usage: python -m src.agent <company_name>")
        sys.exit(1)

    company_name = sys.argv[1]
    print(f"👀 Fetching intel for company: {company_name!r}")

    # 3) Fetch the _raw_ model response
    raw = fetch_intel(company_name)

    # 4) Clean out any markdown fences
    cleaned_str = clean_json_string(raw)

    # 5) Parse into a Python dict (or bail with an error)
    try:
        data = json.loads(cleaned_str)
    except json.JSONDecodeError as e:
        print("❌ Failed to parse JSON:", e)
        print("Raw response was:\n", raw)
        sys.exit(1)

    # 6) Write a nicely‐formatted JSON file
    out_path = f"data/output_{company_name}.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Wrote cleaned JSON to {out_path}")



