import PyPDF2
import re

def extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF at pdf_path."""
    reader = PyPDF2.PdfReader(pdf_path)
    full_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text.append(text)
    return "\n".join(full_text)

def extract_fields(text: str) -> list[str]:
    """
    Extract checklist field titles.
    Matches optional bullet (●), the title, and an optional trailing colon.
    """
    pattern = r"^(?:●\s*)?(.+?)(?:\:\s*)?$"
    return re.findall(pattern, text, flags=re.MULTILINE)

if __name__ == "__main__":
    pdf_file = "data/template.pdf"
    print("Extracting text from:", pdf_file)
    content = extract_text(pdf_file)

    print("\n----- PDF CONTENT START -----")
    print(content)
    print("------ PDF CONTENT END ------\n")

    # Demonstration: extract and display field names
    fields = extract_fields(content)
    print("Found fields:")
    for f in fields:
        print(" -", f)
