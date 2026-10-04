"""Read the look of a PDF CV: its colors, fonts and text sizes, for matching it in my-search/style.css.

  python3 kit/pdf_style.py <cv.pdf>

Colors are exact (read from the PDF itself, not guessed from a picture). Sizes are what each font is drawn at,
with how much text uses it, so the body size and the heading sizes stand out. First page only.
A Word file: save it as PDF first.
"""

import collections
import sys
import pypdf
from pypdf.generic import ContentStream

if len(sys.argv) < 2:
    sys.exit(__doc__)
reader = pypdf.PdfReader(sys.argv[1])
page = reader.pages[0]
fills, strokes = collections.Counter(), collections.Counter()


def hexc(v):
    return "#" + "".join(f"{round(float(x) * 255):02X}" for x in v)


for operands, op in ContentStream(page.get_contents(), reader).operations:
    if op in (b"rg", b"sc", b"scn") and len(operands) == 3:
        fills[hexc(operands)] += 1
    elif op == b"g" and len(operands) == 1:
        fills[hexc(operands * 3)] += 1  # gray
    elif op in (b"RG", b"SC", b"SCN") and len(operands) == 3:
        strokes[hexc(operands)] += 1
sizes = collections.Counter()


def visit(text, cm, tm, font, size):
    if text.strip() and font:
        scale = (tm[0] ** 2 + tm[1] ** 2) ** 0.5 * (cm[0] ** 2 + cm[1] ** 2) ** 0.5
        name = str(font.get("/BaseFont") or font.get("/Name") or "(Type3 font, no name)").lstrip("/").split("+")[-1]
        sizes[(name, round(size * scale, 1))] += len(text.strip())


page.extract_text(visitor_text=visit)
print("Fill colors (text and shapes), most used first:")
for c, n in fills.most_common(8):
    print(f"  {c}  x{n}")
if strokes:
    print("Line colors (rules, borders):")
    for c, n in strokes.most_common(4):
        print(f"  {c}  x{n}")
print("Fonts and sizes (characters drawn):")
for (name, s), n in sorted(sizes.items(), key=lambda x: -x[1])[:12]:
    print(f"  {name:32} {s:5}pt  {n} chars")
