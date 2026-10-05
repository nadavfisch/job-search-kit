"""Reading the user's CV files: Word, PDF, text."""

import os
import shutil
import tempfile
import unittest
import zipfile

from helpers import DEMO, write

from extract_text import extract

NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
)
BODY = """
<w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="9000"/></w:tabs></w:pPr>
  <w:r><w:t>Operations Manager</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>2021-Present</w:t></w:r></w:p>
<w:p><w:r><w:t>Line one</w:t><w:br/><w:t>Line two</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">Cut the close </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>from 3 days</w:t></w:r></w:p>
<w:p><w:r><mc:AlternateContent>
  <mc:Choice Requires="wps"><w:txbxContent><w:p><w:r><w:t>Skills: SQL</w:t></w:r></w:p></w:txbxContent></mc:Choice>
  <mc:Fallback><w:txbxContent><w:p><w:r><w:t>Skills: SQL</w:t></w:r></w:p></w:txbxContent></mc:Fallback>
</mc:AlternateContent></w:r></w:p>
<w:p><w:r><w:instrText>HYPERLINK "mailto:dana@example.com"</w:instrText></w:r><w:r><w:t>dana@example.com</w:t></w:r></w:p>
"""


def docx(path, body, header=None, footer=None):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f"<w:document {NS}><w:body>{body}</w:body></w:document>")
        if header:
            z.writestr("word/header1.xml", f"<w:hdr {NS}><w:p><w:r><w:t>{header}</w:t></w:r></w:p></w:hdr>")
        if footer:
            z.writestr("word/footer1.xml", f"<w:ftr {NS}><w:p><w:r><w:t>{footer}</w:t></w:r></w:p></w:ftr>")


def temp_folder(test):
    folder = tempfile.mkdtemp()
    test.addCleanup(shutil.rmtree, folder, True)
    return folder


class Word(unittest.TestCase):
    def setUp(self):
        path = os.path.join(temp_folder(self), "cv.docx")
        docx(path, BODY, header="Dana Levi | +972 50 000 0000", footer="References on request")
        self.lines = extract(path).splitlines()

    def test_keeps_tabs_and_line_breaks(self):
        self.assertIn("Operations Manager\t2021-Present", self.lines)
        self.assertEqual(self.lines[self.lines.index("Line one") + 1], "Line two")
        self.assertIn("Cut the close from 3 days", self.lines)

    def test_reads_the_page_header_first_and_the_footer_last(self):
        self.assertEqual(self.lines[0], "Dana Levi | +972 50 000 0000")
        self.assertEqual(self.lines[-1], "References on request")

    def test_a_text_box_once_and_no_field_codes(self):
        self.assertEqual(self.lines.count("Skills: SQL"), 1)
        self.assertNotIn("HYPERLINK", "\n".join(self.lines))
        self.assertIn("dana@example.com", self.lines)


class OtherFormats(unittest.TestCase):
    def test_pdf(self):
        text = extract(os.path.join(DEMO, "master", "Robin Sample - Operations & Automation Lead.pdf"))
        for line in (
            "ROBIN SAMPLE",
            "WORK EXPERIENCE",
            "Operations Manager | Acme Analytics - B2B SaaS | 2021-Present",
        ):
            self.assertIn(line, text)

    def test_plain_text(self):
        path = os.path.join(temp_folder(self), "cv.md")
        write(path, "# Dana Levi\n\nOperations")
        self.assertEqual(extract(path), "# Dana Levi\n\nOperations")


if __name__ == "__main__":
    unittest.main()
