"""Pool Keepers: Skimmer x CRM plan for Nathan (PDF, English, as Pedro). Facts checked live 24/11."""
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

OUT = sys.argv[1]
os.makedirs(os.path.dirname(OUT), exist_ok=True)

NAVY = colors.HexColor("#0B3954")
TEAL = colors.HexColor("#087E8B")
SOFT = colors.HexColor("#EAF4F5")
LINE = colors.HexColor("#C9DADC")
WARN = colors.HexColor("#FFF4E0")
INK = colors.HexColor("#1F2A30")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY,
                    alignment=TA_LEFT, spaceAfter=4)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontName="Helvetica", fontSize=10, textColor=TEAL, spaceAfter=14)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=17, textColor=NAVY,
                    spaceBefore=14, spaceAfter=6)
B = ParagraphStyle("B", parent=ss["Normal"], fontName="Helvetica", fontSize=10, leading=14, textColor=INK, spaceAfter=6)
SM = ParagraphStyle("SM", parent=B, fontSize=9, leading=12, spaceAfter=0)
SMB = ParagraphStyle("SMB", parent=SM, fontName="Helvetica-Bold")
TH = ParagraphStyle("TH", parent=SM, fontName="Helvetica-Bold", textColor=colors.white)


def p(t, s=B):
    return Paragraph(t, s)


def bullets(items, style=B):
    return ListFlowable([ListItem(p(i, style), leftIndent=12, value="•") for i in items], bulletType="bullet",
                        start="•", leftIndent=14, bulletFontSize=9)


def table(rows, widths, head=True, zebra=True):
    data = [[p(c, TH if (head and r == 0) else SM) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if head:
        st.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for r in range(1 if head else 0, len(rows)):
            if r % 2 == 0:
                st.append(("BACKGROUND", (0, r), (-1, r), SOFT))
    t.setStyle(TableStyle(st))
    return t


def callout(text, bg=WARN):
    t = Table([[p(text, SM)]], colWidths=[7.0 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def footer(c, d):
    c.saveState()
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#6B7B82"))
    c.drawString(0.75 * inch, 0.5 * inch, "The Pool Keepers · Skimmer + CRM · prepared by Pedro, Pool Profits · Nov 24, 2026")
    c.drawRightString(7.75 * inch, 0.5 * inch, f"Page {d.page}")
    c.restoreState()


s = []
s += [p("Skimmer + your CRM: how they work together", H1),
      p("The Pool Keepers · review of the live connection and my recommendations · November 24, 2026", SUB)]

s += [p("Hi Nathan,"),
      p("Thanks for giving me admin access to Skimmer. I went through every setting of the CRM integration (view only, "
        "nothing was changed) and checked what is actually happening on the CRM side. Here's where things stand, what I "
        "recommend, and the few decisions I need from you. Everything on the CRM side I build and test myself; on your "
        "side it's about 5 minutes of clicks in Skimmer, or we can do them together on a quick call."),
      ]

s += [p("1. The short version", H2),
      bullets([
          "<b>The connection works.</b> Skimmer is connected to the right CRM account (the one your team uses every day), "
          "and Skimmer's activity already shows up on each customer in the CRM as a note, every hour. I checked this on "
          "real customers: work orders scheduled and status changes are there.",
          "<b>New customers are not coming from the pipeline yet.</b> Skimmer creates a customer when a card reaches the "
          "stage \"Customer Pipeline &gt; New Lead\". Your CRM has no cards in any pipeline today, because the flows that "
          "create a card for every new call, form and text are built but still paused, waiting for your OK. So this "
          "trigger has never fired.",
          "<b>Three settings need a tweak</b> (section 3): the initial import is on, the lead source is fixed to "
          "\"Customer referral\" for everyone, and the trigger stage should be your Won stage instead of New Lead.",
          "<b>Once that's set, I can automate the hand-off both ways</b> (section 4): Won in the CRM becomes a customer in "
          "Skimmer, and what happens in Skimmer (customer added, active/inactive, past due, work orders) updates the CRM, "
          "so your leads stop getting sales follow-ups the moment they become customers.",
      ])]

s += [p("2. What's set up in Skimmer today", H2),
      table([
          ["Setting", "Today", "What it means"],
          ["Connection", "Connected to your live CRM account", "Correct account. Nothing to change."],
          ["Initial import (initial contact sync)", "<b>On</b>", "We planned to keep this off on 11/16. Off is safer: your CRM "
           "has about 1,200 contacts, many of them one-time callers and spam."],
          ["Lead conversion (every 15 min)", "On", "A CRM card that reaches the trigger stage becomes a Skimmer customer."],
          ["Contact updates (every 30 min)", "On", "Keeps name, phone, email and address in sync. On 11/20 it also created a "
           "Skimmer customer on its own, for a CRM contact that had just received an address and email (no card involved)."],
          ["Skimmer to CRM (daily) and activity notes (hourly)", "On", "Customer changes and activity reach the CRM. Working."],
          ["Trigger stage", "<b>Customer Pipeline &gt; New Lead</b>", "That pipeline is not the one your lead flows use, "
           "and New Lead would turn every new lead into a customer, even the ones who never sign up."],
          ["Lead source given to new customers", "<b>Customer referral</b>", "Every customer created from the CRM is tagged as a "
           "referral, whatever the real source was (Google, website, call)."],
          ["Create work order on that stage", "Off", "Fine for now; your office schedules the first visit."],
          ["Field mapping", "Name, email, mobile, billing and service address", "Correct. Body of water not mapped (Skimmer "
           "defaults to \"Pool\", 0 gallons)."],
          ["Tags", "Skimmer's own \"created from\" / \"updated from\" CRM tags", "Added on the Skimmer side only. No tag mapping."],
      ], [1.75 * inch, 1.75 * inch, 3.5 * inch])]

s += [p("3. Recommended Skimmer settings (your clicks, about 5 minutes)", H2),
      p("Skimmer &gt; Integrations Center &gt; your CRM integration &gt; Manage &gt; Configure, then Next through the steps "
        "and <b>Finish</b> at the end:"),
      table([
          ["Step", "Change to", "Why"],
          ["Flow settings", "Initial import: <b>Off</b>. Keep the other four on (see decision 2 for contact updates).",
           "Only real customers should become Skimmer customers."],
          ["Trigger", "Pipeline <b>Pool Leads</b>, stage <b>Won - Weekly Pool Service</b>",
           "A customer is created in Skimmer only when your team marks the deal as won."],
          ["Lead source", "A source like <b>\"Website / CRM lead\"</b> (add it in Skimmer's lead sources first) instead of "
           "Customer referral", "Keeps your referral numbers honest in Skimmer reports."],
          ["Work order", "Leave off", "Turn on later if you want Skimmer to open the first service call automatically."],
      ], [1.3 * inch, 3.2 * inch, 2.5 * inch]),
      Spacer(1, 6),
      callout("Skimmer lets you pick one trigger stage. I suggest <b>Won - Weekly Pool Service</b> because those are the "
              "customers you service on routes. One-time repairs and remodels can stay CRM-only, or we add them to "
              "Skimmer by hand when needed.")]

s += [p("4. What I'll build on the CRM side", H2),
      p("All of this goes in paused first. I test it with test contacts only (then delete them) and it goes live only "
        "when you say so. Service messages (on my way, service finished, invoices, quotes) stay in Skimmer; the CRM "
        "won't repeat them."),
      table([
          ["When this happens", "The CRM does this"],
          ["A new call, form or text comes in", "Creates a card in Pool Leads, alerts your team and starts the lead "
           "follow-up texts (these flows are built and waiting for your OK)."],
          ["Your team moves the card to Won - Weekly Pool Service", "Skimmer creates the customer and service location "
           "within 15 minutes (no double entry)."],
          ["Skimmer: customer added, or status changed to Active", "Marks the contact as a customer, stops all lead "
           "follow-ups and moves the card to Won, even if the customer was added in Skimmer first."],
          ["Skimmer: work order scheduled", "Stops any quote follow-up for that contact."],
          ["Skimmer: status changed to Inactive", "Moves the card to Lost. Optional: a friendly win-back text after "
           "45 days (you approve the wording)."],
          ["Skimmer: customer marked past due", "An internal alert to your office only. Skimmer already reminds the "
           "customer, so the CRM won't text them about it."],
          ["Skimmer: work order finished", "Review request, but only if Skimmer's own service feedback is turned off "
           "(see decision 4). Customers should get one ask, not two."],
      ], [2.6 * inch, 4.4 * inch])]

s += [KeepTogether([p("5. Decisions I need from you", H2),
      table([
          ["#", "Question", "My recommendation"],
          ["1", "Can I turn on the lead flows (card + team alert + follow-ups for every new call, form and text)?",
           "Yes. Without them there are no cards, so nothing reaches Skimmer from the pipeline."],
          ["2", "Should a CRM contact become a Skimmer customer only when it's marked Won, or also when it gets an "
           "address and email (what contact updates did on 11/20)?", "Only when Won. If you agree, I'll tell you exactly "
           "which toggle to switch off."],
          ["3", "Lead source for customers created from the CRM.", "\"Website / CRM lead\", or any name you prefer."],
          ["4", "Reviews: Skimmer's service feedback or the CRM's review request (score first, 5 stars go to Google)?",
           "Pick one. I'd use the CRM's because it sends happy customers straight to your Google page."],
          ["5", "Win-back text for customers who go inactive?", "Yes, 45 days after, with wording you approve."],
      ], [0.3 * inch, 3.6 * inch, 3.1 * inch], zebra=True)])]

s += [p("6. Next steps", H2),
      bullets([
          "You reply to the 5 questions (a quick line per question is enough) and make the changes in section 3, or we do "
          "them together on a 15-minute call.",
          "I build the CRM side, test the full path with test contacts (new lead, card to Won, customer in Skimmer, "
          "activity back in the CRM), delete the tests, and send you a short summary before anything goes live.",
      ]),
      Spacer(1, 8),
      p("Pedro")]

doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.7 * inch,
                        bottomMargin=0.8 * inch, title="Skimmer + CRM - The Pool Keepers", author="Pedro, Pool Profits")
doc.build(s, onFirstPage=footer, onLaterPages=footer)
print(OUT)
