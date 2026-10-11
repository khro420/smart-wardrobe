from pathlib import Path
from pypdf import PdfReader

source = Path(r"C:\Users\khorh\OneDrive\Desktop\My Files\FYP\Project 1\RSW_KhorHuaSheng_Project 1.pdf")
reader = PdfReader(source)
queries = ("FastAPI", "mobile web", "PostgreSQL", "three-tier", "system architecture")
for query in queries:
    print(f"\n### {query}\n")
    shown = 0
    for number, page in enumerate(reader.pages, start=1):
        content = page.extract_text() or ""
        if query.lower() in content.lower():
            start = max(0, content.lower().find(query.lower()) - 500)
            print(f"PAGE {number}: {content[start:start+1600]}")
            shown += 1
            if shown == 4:
                break
