from pathlib import Path
import pypdfium2 as pdfium

source = Path(r"C:\Users\khorh\smart-wardrobe\tmp\summary-paper-eight\final-revised.pdf")
output = Path(r"C:\Users\khorh\smart-wardrobe\tmp\summary-paper-eight\rendered-pages-revised")
output.mkdir(parents=True, exist_ok=True)
pdf = pdfium.PdfDocument(source)
for index in range(len(pdf)):
    image = pdf[index].render(scale=1.5).to_pil()
    image.save(output / f"page-{index + 1}.png")
print(len(pdf))
