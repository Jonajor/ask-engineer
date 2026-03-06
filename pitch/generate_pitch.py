"""
Generates the Strata Engineering pitch deck PDF.
Run: python3 generate_pitch.py
Output: strata-engineering-pitch.pdf
"""
from fpdf import FPDF

W = 297   # A4 landscape width (mm)
H = 210   # A4 landscape height (mm)
NAVY  = (26,  58,  92)
BLUE  = (45, 106, 159)
LBLUE = (74, 127, 165)
WHITE = (255, 255, 255)
LGRAY = (245, 247, 250)
GRAY  = (120, 120, 120)
BLACK = (30,  30,  30)
GREEN = (30, 120, 60)
AMBER = (180, 100, 0)


class Deck(FPDF):
    def __init__(self):
        super().__init__(orientation="L", format="A4")
        self.set_auto_page_break(False)
        self.set_margins(0, 0, 0)

    # ── helpers ──────────────────────────────────────────────────────────────

    def bg(self, r, g, b):
        self.set_fill_color(r, g, b)
        self.rect(0, 0, W, H, "F")

    def title_text(self, text, y, size=36, color=WHITE, align="C"):
        self.set_font("Helvetica", "B", size)
        self.set_text_color(*color)
        self.set_xy(20, y)
        self.cell(W - 40, 12, text, align=align)

    def body_text(self, text, x, y, w, size=11, color=BLACK, bold=False):
        self.set_font("Helvetica", "B" if bold else "", size)
        self.set_text_color(*color)
        self.set_xy(x, y)
        self.multi_cell(w, 6, text)

    def bullet(self, text, x, y, w=120, size=11, color=BLACK):
        self.body_text(f"  {text}", x, y, w, size, color)

    def accent_bar(self, h=3, color=LBLUE):
        self.set_fill_color(*color)
        self.rect(0, H - h, W, h, "F")

    def slide_number(self, n, total):
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GRAY)
        self.set_xy(W - 25, H - 8)
        self.cell(20, 5, f"{n} / {total}", align="R")

    def tag(self, label, x, y, bg=LBLUE):
        self.set_fill_color(*bg)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 8)
        self.set_xy(x, y)
        self.cell(len(label) * 2.1 + 6, 6, f"  {label}  ", fill=True)

    def left_panel(self, w=110):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, w, H, "F")

    def divider(self, x, y, w, color=LBLUE):
        self.set_draw_color(*color)
        self.set_line_width(0.5)
        self.line(x, y, x + w, y)

    # ── slides ───────────────────────────────────────────────────────────────

    def slide_cover(self):
        self.add_page()
        # Background gradient effect
        self.set_fill_color(*NAVY)
        self.rect(0, 0, W, H, "F")
        self.set_fill_color(*BLUE)
        self.rect(0, H - 60, W, 60, "F")

        # Accent stripe
        self.set_fill_color(*LBLUE)
        self.rect(0, H // 2 - 2, W, 4, "F")

        # Company name
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(180, 210, 235)
        self.set_xy(20, 38)
        self.cell(W - 40, 8, "STRATA ENGINEERING", align="C")

        # Product title
        self.set_font("Helvetica", "B", 40)
        self.set_text_color(*WHITE)
        self.set_xy(20, 52)
        self.cell(W - 40, 16, "Knowledge Assistant", align="C")

        # Tagline
        self.set_font("Helvetica", "", 15)
        self.set_text_color(180, 210, 235)
        self.set_xy(20, 76)
        self.cell(W - 40, 8,
            "AI-powered building science advisory for your project managers",
            align="C")

        # Bottom info
        self.set_font("Helvetica", "", 10)
        self.set_text_color(180, 210, 235)
        self.set_xy(20, H - 25)
        self.cell(W - 40, 6, "Confidential  |  Product Demo  |  2026", align="C")

        self.slide_number(1, 8)

    def slide_problem(self):
        self.add_page()
        self.bg(*LGRAY)
        self.left_panel(105)

        # Left: big statement
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(180, 210, 235)
        self.set_xy(10, 28)
        self.cell(85, 6, "THE PROBLEM", align="C")

        self.divider(15, 40, 75, WHITE)

        self.set_font("Helvetica", "B", 26)
        self.set_text_color(*WHITE)
        self.set_xy(10, 46)
        self.multi_cell(85, 11,
            "Your engineers answer\nthe same questions\nevery week.")

        self.set_font("Helvetica", "", 10)
        self.set_text_color(180, 210, 235)
        self.set_xy(10, 100)
        self.multi_cell(85, 5,
            "Every new project manager, every\nnew strata client - the same routine\ntechnical questions, pulling time\naway from billable engineering work.")

        # Right: pain points
        pains = [
            ("Repetitive Q&A",
             "PMs ask the same questions about membranes, parkades,\nand warranties again and again."),
            ("Inconsistent answers",
             "Different engineers give slightly different responses,\ncreating confusion for clients."),
            ("Report search is slow",
             "Finding relevant data across dozens of past reports\ntakes 20-30 minutes per query."),
            ("Escalation backlog",
             "Simple questions block PMs and fill engineers'\ninboxes with non-billable work."),
        ]

        y = 30
        for title, detail in pains:
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*NAVY)
            self.set_xy(115, y)
            self.cell(165, 6, title)
            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(*GRAY)
            self.set_xy(115, y + 7)
            self.multi_cell(165, 5, detail)
            y += 36

        self.accent_bar()
        self.slide_number(2, 8)

    def slide_solution(self):
        self.add_page()
        self.bg(*NAVY)

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*LBLUE)
        self.set_xy(20, 25)
        self.cell(W - 40, 6, "THE SOLUTION", align="C")

        self.set_font("Helvetica", "B", 32)
        self.set_text_color(*WHITE)
        self.set_xy(20, 36)
        self.cell(W - 40, 12,
            "An AI assistant trained on your building science knowledge.",
            align="C")

        self.divider(60, 56, W - 120, LBLUE)

        items = [
            ("Instant answers",
             "PMs get accurate, cited responses in seconds\n- any time, any device."),
            ("Your knowledge base",
             "Pre-loaded with BC Strata Act, 2-5-10 warranty,\nenvelope, parkade, mechanical systems."),
            ("Report-aware",
             "Upload any depreciation report or condition\nassessment and ask questions about it."),
            ("Structured analysis",
             "Automatically extracts priorities, EOL components,\nand funding concerns from uploaded reports."),
        ]

        x_positions = [20, 90, 160, 230]
        for i, (title, detail) in enumerate(items):
            x = x_positions[i]
            # Icon box
            self.set_fill_color(*BLUE)
            self.rect(x, 68, 60, 80, "F")

            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*WHITE)
            self.set_xy(x + 2, 74)
            self.multi_cell(56, 6, title)

            self.set_font("Helvetica", "", 9)
            self.set_text_color(180, 210, 235)
            self.set_xy(x + 2, 90)
            self.multi_cell(56, 5, detail)

        self.accent_bar(3, LBLUE)
        self.slide_number(3, 8)

    def slide_features(self):
        self.add_page()
        self.bg(*LGRAY)

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*LBLUE)
        self.set_xy(20, 18)
        self.cell(W - 40, 6, "KEY FEATURES")

        self.set_font("Helvetica", "B", 24)
        self.set_text_color(*NAVY)
        self.set_xy(20, 27)
        self.cell(W - 40, 10, "Everything a project manager needs.")

        self.divider(20, 42, W - 40, LBLUE)

        features = [
            ("Chat Interface",
             "Conversational Q&A with full context history. "
             "Ask follow-up questions naturally.",
             NAVY),
            ("PDF Report Upload",
             "Drag-and-drop any depreciation report or BCA. "
             "Questions are automatically scoped to that document.",
             BLUE),
            ("Report Analyzer",
             "One click: get top priorities, components near end of life, "
             "funding concerns, and escalation items.",
             (30, 100, 60)),
            ("Export to PDF",
             "Export the full Q&A session as a branded Strata Engineering PDF "
             "ready to forward to the strata council.",
             (120, 60, 20)),
            ("Knowledge Base",
             "17 expert knowledge chunks covering BC Strata Act, 2-5-10 warranty, "
             "envelope, parkade, mechanical, fire protection, and more.",
             LBLUE),
            ("Zero AI cost",
             "Uses Groq (free API, llama-3.3-70b) and local embeddings. "
             "No ongoing OpenAI or Azure bills.",
             (60, 110, 60)),
        ]

        col_w = (W - 40) / 3
        positions = [
            (20, 52), (20 + col_w, 52), (20 + col_w * 2, 52),
            (20, 120), (20 + col_w, 120), (20 + col_w * 2, 120),
        ]

        for i, (title, detail, color) in enumerate(features):
            x, y = positions[i]
            self.set_fill_color(*color)
            self.rect(x, y, 4, 30, "F")

            self.set_font("Helvetica", "B", 10.5)
            self.set_text_color(*color)
            self.set_xy(x + 7, y + 2)
            self.cell(col_w - 15, 5, title)

            self.set_font("Helvetica", "", 9)
            self.set_text_color(*GRAY)
            self.set_xy(x + 7, y + 9)
            self.multi_cell(col_w - 15, 4.5, detail)

        self.accent_bar()
        self.slide_number(4, 8)

    def slide_demo(self):
        self.add_page()
        self.bg(*LGRAY)
        self.set_fill_color(*NAVY)
        self.rect(0, 0, W, 45, "F")

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*LBLUE)
        self.set_xy(20, 14)
        self.cell(W - 40, 6, "LIVE DEMO")

        self.set_font("Helvetica", "B", 26)
        self.set_text_color(*WHITE)
        self.set_xy(20, 23)
        self.cell(W - 40, 10, "See it in action.")

        steps = [
            ("1", "Ask a General Question",
             'Try: "Our building in Burnaby was built in 1994. Should we be concerned\n'
             'about the building envelope?" - watch the agent cite sources from BC\n'
             'building science knowledge.'),
            ("2", "Upload a Report",
             'Upload any depreciation report PDF. The agent immediately scopes\n'
             'all questions to that document, pulling relevant context before\n'
             'generating each answer.'),
            ("3", "Run Report Analysis",
             'Click "Run Analysis" to get a structured breakdown: top 5 priorities\n'
             'by urgency, components near end of life, funding concerns, and items\n'
             'that need formal engineer sign-off.'),
            ("4", "Export to PDF",
             'Click "Export Q&A to PDF" in the sidebar. Get a branded Strata\n'
             'Engineering document ready to forward to the strata council or\n'
             'property manager.'),
        ]

        y = 52
        for num, title, detail in steps:
            self.set_fill_color(*NAVY)
            self.set_text_color(*WHITE)
            self.set_font("Helvetica", "B", 14)
            self.rect(20, y, 10, 10, "F")
            self.set_xy(20, y)
            self.cell(10, 10, num, align="C")

            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*NAVY)
            self.set_xy(34, y + 1)
            self.cell(W - 60, 5, title)

            self.set_font("Helvetica", "", 9)
            self.set_text_color(*GRAY)
            self.set_xy(34, y + 8)
            self.multi_cell(W - 60, 4.5, detail)
            y += 38

        self.accent_bar()
        self.slide_number(5, 8)

    def slide_technical(self):
        self.add_page()
        self.bg(*LGRAY)
        self.left_panel(105)

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(180, 210, 235)
        self.set_xy(10, 28)
        self.cell(85, 6, "TECHNICAL", align="C")

        self.divider(15, 40, 75, WHITE)

        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*WHITE)
        self.set_xy(10, 46)
        self.multi_cell(85, 10, "Simple.\nHosted.\nZero-cost AI.")

        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(180, 210, 235)
        self.set_xy(10, 100)
        self.multi_cell(85, 5,
            "No infrastructure to manage.\nNo expensive API bills.\nNo data stored between sessions.")

        stack = [
            ("Frontend",   "Streamlit (Python)",           "Hosted on Streamlit Cloud - free"),
            ("Backend",    "FastAPI (Python)",              "Hosted on Render - free tier"),
            ("LLM",        "Groq / llama-3.3-70b",         "Free API - fast, high quality"),
            ("Embeddings", "fastembed / all-MiniLM-L6-v2", "Local ONNX - no API cost"),
            ("PDF parse",  "pypdf",                        "Runs in backend, no external service"),
            ("Privacy",    "No database / in-memory only", "Reports are not persisted between restarts"),
        ]

        y = 30
        for layer, tech, note in stack:
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*NAVY)
            self.set_xy(115, y)
            self.cell(40, 5, layer)

            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(*BLACK)
            self.set_xy(158, y)
            self.cell(60, 5, tech)

            self.set_font("Helvetica", "I", 8.5)
            self.set_text_color(*GRAY)
            self.set_xy(222, y)
            self.cell(W - 232, 5, note)

            self.set_draw_color(220, 220, 220)
            self.set_line_width(0.2)
            self.line(115, y + 7, W - 15, y + 7)
            y += 14

        self.accent_bar()
        self.slide_number(6, 8)

    def slide_value(self):
        self.add_page()
        self.bg(*NAVY)

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*LBLUE)
        self.set_xy(20, 18)
        self.cell(W - 40, 6, "VALUE PROPOSITION", align="C")

        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*WHITE)
        self.set_xy(20, 28)
        self.cell(W - 40, 10,
            "Give your clients more - without adding headcount.", align="C")

        self.divider(60, 46, W - 120, LBLUE)

        values = [
            ("Time savings",
             "PMs resolve routine questions in seconds.\nEngineers stay focused on billable work.",
             GREEN),
            ("Consistent advice",
             "Every PM gets the same accurate, sourced answers\nbased on your knowledge and their reports.",
             LBLUE),
            ("Client value",
             "Offer report-specific Q&A as a premium service\nalongside depreciation reports and BCAs.",
             BLUE),
            ("White-label ready",
             "Fully customizable branding, knowledge base,\nand workflows for Strata Engineering.",
             AMBER),
        ]

        x_positions = [20, 90, 165, 235]
        for i, (title, detail, color) in enumerate(values):
            x = x_positions[i]
            self.set_fill_color(*color)
            self.rect(x, 58, 60, 3, "F")

            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*WHITE)
            self.set_xy(x, 68)
            self.multi_cell(58, 6, title)

            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(180, 210, 235)
            self.set_xy(x, 84)
            self.multi_cell(58, 5, detail)

        # Bottom quote
        self.set_fill_color(*BLUE)
        self.rect(20, 140, W - 40, 40, "F")
        self.set_font("Helvetica", "I", 13)
        self.set_text_color(*WHITE)
        self.set_xy(30, 150)
        self.multi_cell(W - 60, 7,
            '"Imagine your project manager getting an instant, cited answer '
            'to a building envelope question at 9pm - without calling an engineer."')

        self.accent_bar(3, LBLUE)
        self.slide_number(7, 8)

    def slide_next_steps(self):
        self.add_page()
        self.bg(*LGRAY)
        self.set_fill_color(*NAVY)
        self.rect(0, 0, W, 50, "F")

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*LBLUE)
        self.set_xy(20, 14)
        self.cell(W - 40, 6, "NEXT STEPS")

        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*WHITE)
        self.set_xy(20, 24)
        self.cell(W - 40, 10, "Let's run a pilot.")

        steps = [
            ("Week 1-2",  "Pilot",
             "2-3 PMs test the tool on real active files.\nCollect feedback on answer quality and workflow fit."),
            ("Week 3",    "Customize",
             "Expand knowledge base with Strata Engineering's\nspecific workflows, report templates, and terminology."),
            ("Week 4",    "Refine",
             "Adjust based on pilot feedback. Add any missing\nknowledge chunks. Polish the UI to match your brand."),
            ("Month 2+",  "Scale",
             "Roll out to full team. Explore client-facing access\nas a premium add-on to depreciation report engagements."),
        ]

        y = 62
        for period, title, detail in steps:
            self.tag(period, 20, y, LBLUE)

            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*NAVY)
            self.set_xy(20, y + 10)
            self.cell(W // 4 - 25, 5, title)

            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(*GRAY)
            self.set_xy(20, y + 18)
            self.multi_cell(W // 4 - 25, 4.5, detail)

            y += 0
            # Reposition in 2 columns
            if y == 62:
                pass

        # Actually lay out in 4 columns
        col_w = (W - 40) / 4
        y = 62
        for i, (period, title, detail) in enumerate(steps):
            x = 20 + i * col_w
            self.tag(period, x, y, LBLUE)

            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*NAVY)
            self.set_xy(x, y + 10)
            self.cell(col_w - 8, 5, title)

            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(*GRAY)
            self.set_xy(x, y + 18)
            self.multi_cell(col_w - 8, 4.5, detail)

        # CTA
        self.set_fill_color(*NAVY)
        self.rect(20, 148, W - 40, 40, "F")
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*WHITE)
        self.set_xy(20, 158)
        self.cell(W - 40, 8, "Ready to see it live?", align="C")
        self.set_font("Helvetica", "", 11)
        self.set_text_color(180, 210, 235)
        self.set_xy(20, 170)
        self.cell(W - 40, 6,
            "askstrataengineer.streamlit.app  |  ask-engineer.onrender.com/docs",
            align="C")

        self.accent_bar()
        self.slide_number(8, 8)


def build():
    deck = Deck()
    deck.slide_cover()
    deck.slide_problem()
    deck.slide_solution()
    deck.slide_features()
    deck.slide_demo()
    deck.slide_technical()
    deck.slide_value()
    deck.slide_next_steps()
    deck.output("strata-engineering-pitch.pdf")
    print("Generated: strata-engineering-pitch.pdf")


if __name__ == "__main__":
    build()
