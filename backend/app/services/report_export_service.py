from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.models.finance import ManagementReport


DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME_TYPE = "application/pdf"


def report_export_filename(report: ManagementReport, extension: str) -> str:
    return f"china-finance-report-{report.period}.{extension}"


def build_report_docx(report: ManagementReport) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _content_types_xml())
        package.writestr("_rels/.rels", _root_relationships_xml())
        package.writestr("word/document.xml", _document_xml(report))
    return output.getvalue()


def build_report_pdf(report: ManagementReport) -> bytes:
    lines = _report_lines(report)
    content = _pdf_content_stream(lines)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
        b"/Encoding /UniGB-UCS2-H /DescendantFonts [6 0 R] >>",
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream",
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 2 >> "
        b"/FontDescriptor 7 0 R >>",
        b"<< /Type /FontDescriptor /FontName /STSong-Light /Flags 4 "
        b"/FontBBox [-25 -254 1000 880] /ItalicAngle 0 /Ascent 880 "
        b"/Descent -254 /CapHeight 880 /StemV 80 >>",
    ]
    return _assemble_pdf(objects)


def _content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""


def _root_relationships_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def _document_xml(report: ManagementReport) -> str:
    paragraphs = [
        _word_paragraph(report.title, bold=True, size=32),
        _word_paragraph(f"企业：{report.company_name}"),
        _word_paragraph(f"期间：{report.period}"),
        _word_paragraph(""),
    ]
    for section in report.sections:
        paragraphs.append(_word_paragraph(section.title, bold=True, size=24))
        paragraphs.append(_word_paragraph(section.content))
        paragraphs.append(_word_paragraph(""))

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {''.join(paragraphs)}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>"""


def _word_paragraph(text: str, *, bold: bool = False, size: int = 21) -> str:
    bold_xml = "<w:b/>" if bold else ""
    return (
        "<w:p><w:r><w:rPr>"
        '<w:rFonts w:eastAsia="Microsoft YaHei" w:ascii="Microsoft YaHei" w:hAnsi="Microsoft YaHei"/>'
        f"{bold_xml}<w:sz w:val=\"{size}\"/><w:szCs w:val=\"{size}\"/>"
        "</w:rPr>"
        f"<w:t>{escape(text)}</w:t>"
        "</w:r></w:p>"
    )


def _report_lines(report: ManagementReport) -> list[tuple[str, int]]:
    lines: list[tuple[str, int]] = [(report.title, 18), (f"企业：{report.company_name}", 11), (f"期间：{report.period}", 11)]
    for section in report.sections:
        lines.append(("", 6))
        lines.append((section.title, 13))
        for line in _wrap_text(section.content):
            lines.append((line, 10))
    return lines


def _wrap_text(text: str, max_chars: int = 34) -> list[str]:
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)] or [""]


def _pdf_content_stream(lines: list[tuple[str, int]]) -> bytes:
    commands: list[str] = []
    y = 790
    for text, size in lines:
        if y < 70:
            break
        if not text:
            y -= 10
            continue
        commands.append(f"BT /F1 {size} Tf 52 {y} Td <{text.encode('utf-16-be').hex().upper()}> Tj ET")
        y -= size + 8
    return "\n".join(commands).encode("ascii")


def _assemble_pdf(objects: list[bytes]) -> bytes:
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, payload in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(payload)
        output.write(b"\nendobj\n")

    xref_position = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF".encode("ascii")
    )
    return output.getvalue()
