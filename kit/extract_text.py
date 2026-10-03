"""Print the text of a CV or any document: PDF, Word (.docx), or plain text / Markdown.

  python3 kit/extract_text.py path/to/cv.pdf

A scanned PDF (an image, no text layer) prints nothing. Then read it as an image, or ask for a Word/text version.
"""
import re, sys, zipfile
from xml.etree import ElementTree


def extract(path):
    low = path.lower()
    if low.endswith(".pdf"):
        import pypdf
        return "\n\n".join(p.extract_text() or "" for p in pypdf.PdfReader(path).pages)
    if low.endswith(".docx"):
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        root = ElementTree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
        return "\n".join("".join(t.text or "" for t in p.iter(ns + "t")) for p in root.iter(ns + "p"))
    if low.endswith(".doc"):
        sys.exit("Old .doc format: save it as .docx or PDF first.")
    return open(path, encoding="utf-8", errors="ignore").read()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    text = extract(sys.argv[1])
    print(re.sub(r"\n{3,}", "\n\n", text).strip() or "(no text found: scanned PDF? read it as an image instead)")
