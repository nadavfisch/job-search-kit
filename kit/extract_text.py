"""Print the text of a CV or any document: PDF, Word (.docx), or plain text / Markdown.

  python3 kit/extract_text.py path/to/cv.pdf

A scanned PDF (an image, no text layer) prints nothing. Then read it as an image, or ask for a Word/text version.
"""
import re, sys, zipfile
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"   # a second copy of a text box
MARKS = {W + "tab": "\t", W + "br": "\n", W + "cr": "\n", W + "noBreakHyphen": "-"}


def docx_part(xml):
    """The text of one part of a .docx (the body, a header, a footer) in reading order, a line per paragraph.
    Tabs (often the gap between a role and its dates) and line breaks are kept."""
    out = []

    def walk(el):
        if el.tag == FALLBACK or el.tag.endswith("Pr"):   # formatting (tab stops, fonts...), not text
            return
        if el.tag == W + "t":
            out.append(el.text or "")
        elif el.tag in MARKS:
            out.append(MARKS[el.tag])
        for child in el:
            walk(child)
        if el.tag == W + "p":
            out.append("\n")
    walk(ElementTree.fromstring(xml))
    return "".join(out)


def extract(path):
    low = path.lower()
    if low.endswith(".pdf"):
        import pypdf
        return "\n\n".join(p.extract_text() or "" for p in pypdf.PdfReader(path).pages)
    if low.endswith(".docx"):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            # Contact details often sit in the page header, so headers come first and footers last.
            order = ([n for n in names if re.fullmatch(r"word/header\d*\.xml", n)] + ["word/document.xml"]
                     + [n for n in names if re.fullmatch(r"word/footer\d*\.xml", n)])
            return "\n\n".join(filter(None, (docx_part(z.read(n)).strip() for n in order)))
    if low.endswith(".doc"):
        sys.exit("Old .doc format: save it as .docx or PDF first.")
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    text = extract(sys.argv[1])
    print(re.sub(r"\n{3,}", "\n\n", text).strip() or "(no text found: scanned PDF? read it as an image instead)")
