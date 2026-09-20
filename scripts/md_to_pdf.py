"""Build OPERATOR_GUIDE.pdf from OPERATOR_GUIDE.md."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "OPERATOR_GUIDE.md"
OUTPUT = ROOT / "OPERATOR_GUIDE.pdf"

NAVY = colors.HexColor("#1B365D")
TEAL = colors.HexColor("#0F6C8C")
ROW_ALT = colors.HexColor("#F3F6F9")
CODE_BG = colors.HexColor("#EEF2F5")
RULE = colors.HexColor("#C5D0DA")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=22,
            leading=28,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=12,
            leading=16,
            textColor=TEAL,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#445566"),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=16,
            leading=20,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=13,
            leading=17,
            textColor=TEAL,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName="Times-Bold",
            fontSize=11.5,
            leading=15,
            textColor=NAVY,
            spaceBefore=9,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=14,
            leftIndent=12,
            spaceAfter=3,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8.5,
            leading=11.5,
            alignment=TA_LEFT,
        ),
        "cell_head": ParagraphStyle(
            "cell_head",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),
        "code": ParagraphStyle(
            "code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8.5,
            leading=12,
            backColor=CODE_BG,
            leftIndent=4,
            rightIndent=4,
            spaceBefore=4,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            textColor=colors.HexColor("#667788"),
            alignment=TA_CENTER,
        ),
    }


def _inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"`([^`]+)`", r'<font face="Courier" size="9">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


def _split_row(line: str) -> list[str]:
    parts = [part.strip() for part in line.strip().strip("|").split("|")]
    return parts


def _is_table_divider(line: str) -> bool:
    core = line.strip().strip("|").replace(":", "").replace("-", "").replace("|", "").replace(" ", "")
    return line.strip().startswith("|") and core == ""


def _parse(md: str) -> list[tuple]:
    lines = md.splitlines()
    blocks: list[tuple] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
        elif line.strip() == "---":
            blocks.append(("hr", ""))
        elif line.startswith("```"):
            lang = line.strip("`").strip()
            chunk: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                chunk.append(lines[i])
                i += 1
            blocks.append(("code", "\n".join(chunk), lang))
        elif line.strip().startswith("|") and i + 1 < len(lines) and _is_table_divider(lines[i + 1]):
            header = _split_row(line)
            i += 2
            rows = [header]
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            i -= 1
            blocks.append(("table", rows))
        elif re.match(r"^\d+\.\s+", line.strip()):
            items: list[str] = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            i -= 1
            blocks.append(("ol", items))
        elif line.strip().startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            i -= 1
            blocks.append(("ul", items))
        elif line.strip():
            para = [line.strip()]
            i += 1
            while (
                i < len(lines)
                and lines[i].strip()
                and not lines[i].startswith("#")
                and not lines[i].startswith("```")
                and not lines[i].strip().startswith("|")
                and not lines[i].strip().startswith("- ")
                and not re.match(r"^\d+\.\s+", lines[i].strip())
                and lines[i].strip() != "---"
            ):
                para.append(lines[i].strip())
                i += 1
            i -= 1
            blocks.append(("p", " ".join(para)))
        i += 1
    return blocks


def _table(rows: list[list[str]], styles: dict[str, ParagraphStyle], width: float) -> Table:
    ncols = max(len(row) for row in rows)
    col_w = width / ncols
    data = []
    for r, row in enumerate(rows):
        padded = row + [""] * (ncols - len(row))
        style = styles["cell_head"] if r == 0 else styles["cell"]
        data.append([Paragraph(_inline(cell), style) for cell in padded])
    table = Table(data, colWidths=[col_w] * ncols, hAlign="LEFT", repeatRows=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, RULE),
    ]
    for r in range(1, len(rows)):
        if r % 2 == 0:
            commands.append(("BACKGROUND", (0, r), (-1, r), ROW_ALT))
    table.setStyle(TableStyle(commands))
    return table


def _header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 12 * mm, A4[0], 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Bold", 8)
    canvas.drawString(18 * mm, A4[1] - 7.5 * mm, "Utility Asset Registry")
    canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 7.5 * mm, "Operator guide")
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, A4[0], 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Roman", 8)
    canvas.drawCentredString(A4[0] / 2, 5 * mm, f"Page {doc.page}  ·  For IT, night operator, day staff, administrator and supervisor")
    canvas.restoreState()


def build() -> Path:
    styles = _styles()
    md = SOURCE.read_text(encoding="utf-8")
    # Drop the first H1; cover page uses it.
    body_md = re.sub(r"^# .+\n+", "", md, count=1)
    blocks = _parse(body_md)
    width = A4[0] - 36 * mm

    story = [
        Spacer(1, 28 * mm),
        Paragraph("Utility Asset Registry", styles["cover_title"]),
        Paragraph("How to operate this system", styles["cover_sub"]),
        Spacer(1, 4 * mm),
        HRFlowable(width="100%", thickness=1.2, color=NAVY, spaceAfter=8),
        Paragraph("Electricity distribution utility · Bhubaneswar", styles["cover_meta"]),
        Paragraph("Simple command guide for different users", styles["cover_meta"]),
        Paragraph("20 September 2026", styles["cover_meta"]),
        Spacer(1, 10 * mm),
        Paragraph(
            "This booklet is for people who run the system day to day. "
            "You do not need to know Python. Read only the section for your job: "
            "IT (Section A), night operator (Section B), day staff / surveyor (Section C), "
            "administrator (Section D), or supervisor (Section E).",
            styles["body"],
        ),
        Paragraph(
            "Project folder: <font face='Courier' size='9'>C:\\Users\\ranja\\utility-asset-registry</font>",
            styles["cover_meta"],
        ),
        PageBreak(),
    ]

    for block in blocks:
        kind = block[0]
        if kind == "h1":
            story.append(Paragraph(_inline(block[1]), styles["h1"]))
        elif kind == "h2":
            story.append(Paragraph(_inline(block[1]), styles["h2"]))
        elif kind == "h3":
            story.append(Paragraph(_inline(block[1]), styles["h3"]))
        elif kind == "p":
            story.append(Paragraph(_inline(block[1]), styles["body"]))
        elif kind == "hr":
            story.append(HRFlowable(width="100%", thickness=0.4, color=RULE, spaceBefore=4, spaceAfter=8))
        elif kind == "code":
            story.append(Preformatted(block[1] or " ", styles["code"]))
        elif kind == "ul":
            items = [
                ListItem(Paragraph(_inline(item), styles["bullet"]), leftIndent=8, bulletColor=TEAL)
                for item in block[1]
            ]
            story.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=12, spaceAfter=6))
        elif kind == "ol":
            items = [
                ListItem(Paragraph(_inline(item), styles["bullet"]), leftIndent=8)
                for item in block[1]
            ]
            story.append(ListFlowable(items, bulletType="1", leftIndent=12, spaceAfter=6))
        elif kind == "table":
            story.append(KeepTogether([_table(block[1], styles, width), Spacer(1, 6)]))

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="Utility Asset Registry — Operator Guide",
        author="Utility Asset Registry",
        subject="How to operate the system for IT, night operator, day staff, administrator and supervisor",
    )
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(path)
    print(f"bytes={path.stat().st_size}")
