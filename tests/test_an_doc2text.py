import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "kit", ".claude", "skills", "tl-analytics", "scripts"))
import an_doc2text  # noqa: E402

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
S = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
REL = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


def make_zip(path, parts):
    with zipfile.ZipFile(path, "w") as z:
        for name, content in parts.items():
            z.writestr(name, content)


class Doc2TextTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def path(self, name):
        return os.path.join(self.dir, name)

    def test_docx_hebrew_headings_and_table(self):
        p = self.path("process.docx")
        make_zip(p, {"word/document.xml": f"""<w:document {W}><w:body>
            <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>תהליך אישור שיקים</w:t></w:r></w:p>
            <w:p><w:r><w:t xml:space="preserve">כיום כ-8% </w:t></w:r><w:r><w:t>מאושרים אוטומטית.</w:t></w:r></w:p>
            <w:tbl><w:tr><w:tc><w:p><w:r><w:t>קוד</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>משמעות</w:t></w:r></w:p></w:tc></w:tr>
                   <w:tr><w:tc><w:p><w:r><w:t>AMOUNT_LIMIT</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>מעל 1,000</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
            </w:body></w:document>"""})
        text = an_doc2text.convert(p)
        self.assertIn("# תהליך אישור שיקים", text)
        self.assertIn("כיום כ-8% מאושרים אוטומטית.", text)
        self.assertIn("| AMOUNT_LIMIT | מעל 1,000 |", text)

    def test_xlsx_shared_and_inline_strings(self):
        p = self.path("limits.xlsx")
        make_zip(p, {
            "xl/workbook.xml": f'<workbook {S} {R}><sheets><sheet name="ספים" sheetId="1" r:id="rId1"/></sheets></workbook>',
            "xl/_rels/workbook.xml.rels": f'<Relationships {REL}><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="x"/></Relationships>',
            "xl/sharedStrings.xml": f'<sst {S}><si><t>פרמטר</t></si><si><t>ערך</t></si><si><t>AMOUNT_LIMIT</t></si></sst>',
            "xl/worksheets/sheet1.xml": f"""<worksheet {S}><sheetData>
                <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
                <row r="2"><c r="A2" t="s"><v>2</v></c><c r="C2"><v>1000</v></c></row>
                <row r="3"><c r="A3" t="inlineStr"><is><t>הערה</t></is></c></row>
                </sheetData></worksheet>"""})
        text = an_doc2text.convert(p)
        self.assertIn("## Sheet: ספים", text)
        self.assertIn("| פרמטר | ערך |", text)
        self.assertIn("| AMOUNT_LIMIT |  | 1000 |", text)
        self.assertIn("| הערה |", text)

    def test_xlsx_max_rows(self):
        p = self.path("big.xlsx")
        rows = "".join(f'<row r="{i}"><c r="A{i}"><v>{i}</v></c></row>' for i in range(1, 11))
        make_zip(p, {
            "xl/workbook.xml": f'<workbook {S} {R}><sheets><sheet name="S" sheetId="1" r:id="rId1"/></sheets></workbook>',
            "xl/_rels/workbook.xml.rels": f'<Relationships {REL}><Relationship Id="rId1" Target="/xl/worksheets/sheet1.xml" Type="x"/></Relationships>',
            "xl/worksheets/sheet1.xml": f"<worksheet {S}><sheetData>{rows}</sheetData></worksheet>"})
        text = an_doc2text.convert(p, max_rows=3)
        self.assertIn("| 3 |", text)
        self.assertNotIn("| 4 |", text)
        self.assertIn("more rows not shown", text)

    def test_pptx_slides_in_order(self):
        p = self.path("deck.pptx")
        slide = lambda t: f"<p:sld xmlns:p='x' {A}><a:p><a:r><a:t>{t}</a:t></a:r></a:p></p:sld>"
        make_zip(p, {"ppt/slides/slide10.xml": slide("עשר"), "ppt/slides/slide2.xml": slide("שתיים")})
        text = an_doc2text.convert(p)
        self.assertLess(text.index("שתיים"), text.index("עשר"))

    def test_unsupported_format(self):
        p = self.path("old.doc")
        open(p, "wb").close()
        with self.assertRaises(ValueError):
            an_doc2text.convert(p)

    def test_cli_out_file_is_utf8(self):
        src = self.path("a.md")
        with open(src, "w", encoding="utf-8") as f:
            f.write("פקיד")
        out = self.path("out.txt")
        self.assertEqual(an_doc2text.main([src, "--out", out]), 0)
        with open(out, encoding="utf-8") as f:
            self.assertIn("פקיד", f.read())

    def test_cli_reports_bad_file_and_continues(self):
        good = self.path("ok.txt")
        with open(good, "w", encoding="utf-8") as f:
            f.write("ok")
        out = self.path("out.txt")
        import io
        import contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            code = an_doc2text.main([self.path("missing.docx"), good, "--out", out])
        self.assertEqual(code, 1)
        with open(out, encoding="utf-8") as f:
            self.assertIn("ok", f.read())


if __name__ == "__main__":
    unittest.main()
