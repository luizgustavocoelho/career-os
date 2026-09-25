"""Plain, single-column résumé exports with escaped content and no active objects."""

from html import escape
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape
from zipfile import ZIP_DEFLATED, ZipFile

HEADINGS = {"COMPETÊNCIAS", "EXPERIÊNCIA", "PROJETOS", "FORMAÇÃO", "CERTIFICAÇÕES"}


def resume_html(text):
    paragraphs = []
    for index, line in enumerate(text.splitlines()):
        tag = "h1" if index == 0 else "h2" if line in HEADINGS else "p"
        paragraphs.append(f"<{tag}>{escape(line)}</{tag}>")
    return (
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Currículo</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<style>body{font:11pt Arial,sans-serif;line-height:1.4;max-width:180mm;margin:20mm auto;color:#111;padding:0 8mm}h1{font-size:20pt}h2{font-size:12pt;margin-top:18pt;break-after:avoid}p{white-space:pre-wrap;overflow-wrap:anywhere;margin:5pt 0}@page{margin:20mm}@media print{body{margin:0;padding:0}}</style>"
        "<body>" + "\n".join(paragraphs) + "</body></html>"
    ).encode("utf-8")


def resume_docx(text):
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    paragraphs = []
    for index, line in enumerate(text.splitlines()):
        style = "Title" if index == 0 else "Heading1" if line in HEADINGS else "Normal"
        # XML 1.0 excludes control characters that may be present in extracted PDFs.
        line = "".join(c for c in line if ord(c) >= 32 or c == "\t")
        paragraphs.append(
            f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t xml:space="preserve">{xml_escape(line)}</w:t></w:r></w:p>'
        )
    document = (
        f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{ns}"><w:body>'
        + "".join(paragraphs)
        + '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'
    )
    styles = f'''<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="{ns}">
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="100" w:line="276" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="22"/><w:color w:val="111111"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:after="180"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/><w:color w:val="000000"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="100"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style></w:styles>'''
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        )
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", styles)
    return output.getvalue()
