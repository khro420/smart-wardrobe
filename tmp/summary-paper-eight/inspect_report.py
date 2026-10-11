from pathlib import Path
from pypdf import PdfReader

source = Path(r"C:\Users\khorh\OneDrive\Desktop\My Files\FYP\Project 1\RSW_KhorHuaSheng_Project 1.pdf")
reader = PdfReader(source)
print(f"pages {len(reader.pages)}")
terms = ("architecture", "fastapi", "system design", "technology stack", "workflow")
for number, page in enumerate(reader.pages, start=1):
    content = page.extract_text() or ""
    if any(term in content.lower() for term in terms):
        print(f"\nPAGE {number}\n{content[:2400]}")
