import re
from datetime import datetime
from fpdf import FPDF

LEFT_MARGIN = 15
RIGHT_MARGIN = 15
PAGE_WIDTH = 210
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN  # 180mm


def _clean(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", text, flags=re.DOTALL)
    return text.strip()


class _PDF(FPDF):
    def header(self):
        # Logo / company name
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(26, 58, 92)
        self.set_x(LEFT_MARGIN)
        self.cell(90, 10, "Strata Engineering", ln=False)

        # Subtitle right-aligned
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, "Knowledge Assistant  |  Session Export", align="R", ln=True)

        # Horizontal rule
        self.set_draw_color(208, 228, 240)
        self.set_line_width(0.5)
        self.line(LEFT_MARGIN, self.get_y(), PAGE_WIDTH - RIGHT_MARGIN, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(208, 228, 240)
        self.set_line_width(0.3)
        self.line(LEFT_MARGIN, self.get_y(), PAGE_WIDTH - RIGHT_MARGIN, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(150, 150, 150)
        self.set_x(LEFT_MARGIN)
        self.cell(
            CONTENT_WIDTH - 15, 5,
            "This document does not replace formal engineering review or sign-off.",
            ln=False,
        )
        self.cell(15, 5, f"Page {self.page_no()}", align="R")

    def tag(self, label: str, r: int, g: int, b: int):
        """Print a small coloured label pill."""
        self.set_x(LEFT_MARGIN)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(255, 255, 255)
        self.set_fill_color(r, g, b)
        self.cell(len(label) * 2.2 + 4, 5, f"  {label}  ", fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(255, 255, 255)

    def body_text(self, text: str, indent: int = 0):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.set_x(LEFT_MARGIN + indent)
        self.multi_cell(CONTENT_WIDTH - indent, 5.5, text)

    def sources_line(self, sources: list):
        if not sources:
            return
        self.set_x(LEFT_MARGIN)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(130, 130, 130)
        for s in sources:
            self.set_x(LEFT_MARGIN + 2)
            self.multi_cell(CONTENT_WIDTH - 2, 4, f"- {s}")
        self.set_text_color(0, 0, 0)

    def divider(self):
        self.ln(2)
        self.set_draw_color(230, 230, 230)
        self.set_line_width(0.2)
        self.line(LEFT_MARGIN, self.get_y(), PAGE_WIDTH - RIGHT_MARGIN, self.get_y())
        self.ln(4)


def generate_pdf(messages: list, report_name: str | None = None) -> bytes:
    pdf = _PDF()
    pdf.set_margins(LEFT_MARGIN, 15, RIGHT_MARGIN)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Meta row
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(100, 100, 100)
    pdf.set_x(LEFT_MARGIN)
    date_str = datetime.now().strftime("%B %d, %Y  %H:%M")
    pdf.cell(CONTENT_WIDTH // 2, 5, f"Exported: {date_str}", ln=False)
    if report_name:
        pdf.cell(0, 5, f"Report: {report_name}", align="R", ln=True)
    else:
        pdf.ln()

    pdf.ln(3)

    # Disclaimer box
    pdf.set_fill_color(240, 248, 255)
    pdf.set_draw_color(74, 127, 165)
    pdf.set_line_width(0.3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(60, 100, 140)
    pdf.set_x(LEFT_MARGIN)
    pdf.multi_cell(
        CONTENT_WIDTH, 4.5,
        "This Q&A session was generated using AI-assisted building science knowledge. "
        "Content should be reviewed by a qualified engineer before being used for formal "
        "recommendations, legal purposes, or strata council decisions.",
        border=1, fill=True,
    )
    pdf.ln(6)
    pdf.set_text_color(0, 0, 0)

    for msg in messages:
        role = msg.get("role", "")
        content = _clean(msg.get("content", ""))
        sources = msg.get("sources", [])

        if role == "user":
            pdf.tag("PROJECT MANAGER", 80, 100, 120)
            pdf.ln(1)
            pdf.body_text(content)
            pdf.ln(4)

        elif role == "assistant":
            pdf.tag("STRATA ENGINEERING ASSISTANT", 26, 58, 92)
            pdf.ln(1)
            pdf.body_text(content)
            if sources:
                pdf.ln(1)
                pdf.sources_line(sources)
            pdf.divider()

    return bytes(pdf.output())
