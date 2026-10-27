#!/usr/bin/env python3
"""Clear Pool Solutions Tucson: lead & conversion report PDF for Derek (Pedro, 27/10).

    ./.venv/bin/python scripts/cp_results_report.py <leads_by_month.csv>

The CSV (month, source, leads, won, spam) comes from the account's contacts: a lead = tagged `new lead` (or `won`) by
our intake automations, spam = tagged spam/dnd/spam likely, customer = tagged `won` (card moved to a Won stage).
Benchmarks are cited with their source. Writes reports/clear-pool-tucson/*.html and .pdf (gitignored).
"""
from __future__ import annotations

import csv
import subprocess
import sys
from collections import defaultdict
from datetime import date

from _common import ROOT

CHROMIUM = "/opt/pw-browsers/chromium"
OUT = ROOT / "reports" / "clear-pool-tucson"
WEEKLY, REPAIR = 2160, 150  # Derek's values: weekly customer / one-time repair
WON_WEEKLY, WON_REPAIR = 16, 21  # Won cards by stage, 27/10
CARDS_BEFORE, CARDS_NOW, OPEN_NOW = 233, 114, 4  # pipeline before / after spam and out-of-area cards were removed; open now
CALLS = {"window": "Sep 29 – Oct 27", "total": 46, "answered": 19, "not_answered": 13, "menu": 14}
MONTHS = {"2026-04": "Apr", "2026-05": "May", "2026-06": "Jun", "2026-07": "Jul", "2026-08": "Aug",
          "2026-09": "Sep", "2026-10": "Oct*"}
BENCH = [
    ("Plumbing, lead → job", "12–16%", "WebFX data, cited by PipelineOn",
     "https://pipelineon.com/blog/10-marketing-metrics-home-service-owners/"),
    ("HVAC, lead → job", "8–12%", "WebFX data, cited by PipelineOn",
     "https://pipelineon.com/blog/10-marketing-metrics-home-service-owners/"),
    ("Leads from search ads (all industries)", "7.3%", "LocaliQ, cited by PipelineOn",
     "https://pipelineon.com/blog/10-marketing-metrics-home-service-owners/"),
    ("Home-services callers who reach a person", "52%", "Invoca, 2026 Home Services Benchmarks",
     "https://invoca.com/reports/the-invoca-home-services-lead-conversion-benchmarks-report-2026"),
]


def pct(a: int, b: int) -> str:
    return f"{round(100 * a / b)}%" if b else "–"


def chart(months: list[tuple[str, dict]]) -> str:
    w, h, ml, mb, mt = 640, 230, 34, 28, 18
    top = max(m["leads"] for _, m in months)
    top = (top // 10 + 1) * 10
    bw = (w - ml - 10) / len(months)
    y = lambda v: h - mb - (h - mb - mt) * v / top  # noqa: E731
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Leads and new customers by month">']
    for t in range(0, top + 1, 10):
        out.append(f'<line x1="{ml}" x2="{w - 10}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="grid"/>'
                   f'<text x="{ml - 6}" y="{y(t) + 4:.1f}" class="tick" text-anchor="end">{t}</text>')
    for i, (label, m) in enumerate(months):
        x = ml + i * bw + bw * 0.2
        bwi = bw * 0.6
        out.append(f'<rect x="{x:.1f}" y="{y(m["leads"]):.1f}" width="{bwi:.1f}" height="{y(0) - y(m["leads"]):.1f}" rx="3" class="lead"/>'
                   f'<rect x="{x:.1f}" y="{y(m["won"]):.1f}" width="{bwi:.1f}" height="{y(0) - y(m["won"]):.1f}" rx="3" class="won"/>'
                   f'<text x="{x + bwi / 2:.1f}" y="{y(m["leads"]) - 5:.1f}" class="val" text-anchor="middle">{m["won"]} / {m["leads"]}</text>'
                   f'<text x="{x + bwi / 2:.1f}" y="{h - 9}" class="tick" text-anchor="middle">{label}</text>')
    return "".join(out) + "</svg>"


def main() -> int:
    rows = list(csv.DictReader(open(sys.argv[1])))
    by_month: dict = defaultdict(lambda: {"leads": 0, "won": 0, "spam": 0})
    by_src: dict = defaultdict(lambda: {"leads": 0, "won": 0, "spam": 0})
    for r in rows:
        for agg in (by_month[r["month"]], by_src[r["source"]]):
            for k in ("leads", "won", "spam"):
                agg[k] += int(r[k])
    leads = sum(m["leads"] for m in by_month.values())
    won = sum(m["won"] for m in by_month.values())
    spam = sum(m["spam"] for m in by_month.values())
    months = [(MONTHS[k], by_month[k]) for k in sorted(by_month)]
    src_rows = "".join(
        f"<tr><td>{s}</td><td class=n>{v['leads']}</td><td class=n>{v['won']}</td><td class=n>{pct(v['won'], v['leads'])}</td>"
        f"<td class=n>{v['spam']}</td></tr>"
        for s, v in sorted(by_src.items(), key=lambda kv: -kv[1]["leads"]) if v["leads"] or v["won"])
    month_rows = "".join(f"<tr><td>{lab}</td><td class=n>{m['leads']}</td><td class=n>{m['won']}</td>"
                         f"<td class=n>{pct(m['won'], m['leads'])}</td><td class=n>{m['spam']}</td></tr>" for lab, m in months)
    won_value = WON_WEEKLY * WEEKLY + WON_REPAIR * REPAIR
    bench = "".join(f'<tr><td>{a}</td><td class=n>{b}</td><td class=src><a href="{u}">{c}</a></td></tr>' for a, b, c, u in BENCH)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Clear Pool Solutions Tucson – Lead Report</title>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
@page {{ size: Letter; margin: 14mm 14mm 16mm; }}
:root {{ --ink:#14212b; --muted:#5b6b78; --line:#d9e1e7; --panel:#f3f7f9; --water:#0e7c9a; --won:#1f8f5f; --lead:#b9cbd5; }}
* {{ box-sizing:border-box; }}
body {{ font-family:Inter,Arial,sans-serif; color:var(--ink); font-size:10.5pt; line-height:1.45; margin:0; }}
h1 {{ font-family:'Source Serif 4',Georgia,serif; font-weight:600; font-size:24pt; margin:0 0 2mm; letter-spacing:-.01em; }}
h2 {{ font-family:'Source Serif 4',Georgia,serif; font-weight:600; font-size:14.5pt; margin:0 0 2mm; }}
.kicker {{ text-transform:uppercase; letter-spacing:.12em; font-size:8pt; color:var(--water); font-weight:600; }}
.sub {{ color:var(--muted); margin:0; }}
header {{ border-bottom:2px solid var(--water); padding-bottom:4mm; margin-bottom:6mm; }}
.tiles {{ display:grid; grid-template-columns:repeat(4,1fr); gap:3mm; margin-bottom:6mm; }}
.tile {{ background:var(--panel); border-radius:3mm; padding:3.5mm 4mm; }}
.tile b {{ display:block; font-family:'Source Serif 4',Georgia,serif; font-size:21pt; font-weight:600; color:var(--water); font-variant-numeric:tabular-nums; }}
.tile span {{ font-size:8.5pt; color:var(--muted); }}
section {{ margin-bottom:4.5mm; break-inside:avoid; }}
p {{ margin:0 0 2.5mm; max-width:175mm; }}
table {{ width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; margin-top:2mm; }}
th {{ text-align:left; font-size:8pt; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); font-weight:600; border-bottom:1px solid var(--line); padding:1.6mm 2mm; }}
td {{ border-bottom:1px solid var(--line); padding:1.6mm 2mm; }}
.n {{ text-align:right; }} th.n {{ text-align:right; }}
td.src {{ font-size:8.5pt; color:var(--muted); }} td.src a {{ color:var(--muted); }}
tr.hi td {{ font-weight:600; background:#e8f4ef; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:6mm; }}
.grid {{ stroke:var(--line); }} .tick {{ font-size:10px; fill:var(--muted); }} .val {{ font-size:10px; fill:var(--ink); font-weight:600; }}
.lead {{ fill:var(--lead); }} .won {{ fill:var(--won); }}
.legend {{ font-size:8.5pt; color:var(--muted); display:flex; gap:5mm; }}
.sw {{ display:inline-block; width:3mm; height:3mm; border-radius:.6mm; vertical-align:-.4mm; margin-right:1.5mm; }}
.callout {{ border-left:3px solid var(--water); background:var(--panel); padding:3mm 4mm; border-radius:0 2mm 2mm 0; }}
ul {{ margin:1mm 0 0; padding-left:5mm; }} li {{ margin-bottom:.8mm; }}
.page-break {{ break-before:page; }}
.foot {{ font-size:8pt; color:var(--muted); }}
</style></head><body>
<header>
  <div class="kicker">Pool Profits · Results report</div>
  <h1>Clear Pool Solutions Tucson</h1>
  <p class="sub">Leads and new customers from the phone lines, texts and forms we run · April – October 2026 · prepared {date(2026, 10, 27):%B %-d, %Y}</p>
</header>

<div class="tiles">
  <div class="tile"><b>{leads}</b><span>real leads (spam removed)</span></div>
  <div class="tile"><b>{won}</b><span>became customers</span></div>
  <div class="tile"><b>{pct(won, leads)}</b><span>of real leads became customers</span></div>
  <div class="tile"><b>${won_value:,}</b><span>in customer value ({WON_WEEKLY} weekly at ${WEEKLY:,}, {WON_REPAIR} repairs at ${REPAIR})</span></div>
</div>

<section>
  <h2>What your conversion rate really is</h2>
  <p>Until now the GHL dashboard showed about <b>{pct(won, CARDS_BEFORE)}</b>: it divided your {won} customers by <i>every</i> card in the
  pipeline ({CARDS_BEFORE}), including {spam} spam calls and robocalls and 18 people outside your service area, who were never real prospects.
  Those cards are now removed automatically. Your pipeline today holds {CARDS_NOW} real opportunities: {won} won, {CARDS_NOW - won - OPEN_NOW} lost
  and {OPEN_NOW} still open.</p>
  <table><thead><tr><th>How it is counted</th><th class=n>Customers ÷ leads</th><th class=n>Rate</th></tr></thead><tbody>
    <tr><td>GHL dashboard before the cleanup (spam included)</td><td class=n>{won} ÷ {CARDS_BEFORE}</td><td class=n>{pct(won, CARDS_BEFORE)}</td></tr>
    <tr class=hi><td>Every real lead we tracked (this report)</td><td class=n>{won} ÷ {leads}</td><td class=n>{pct(won, leads)}</td></tr>
    <tr><td>Pipeline now: won ÷ all opportunities (open, won, lost)</td><td class=n>{won} ÷ {CARDS_NOW}</td><td class=n>{pct(won, CARDS_NOW)}</td></tr>
  </tbody></table>
</section>

<section>
  <h2>How that compares</h2>
  <p>There is no published industry benchmark for pool service specifically, so the closest comparisons are other home-service
  trades. Even on the old count that included spam, your rate sat at the top of the plumbing range and above HVAC; on real
  leads it is well above both.</p>
  <table><thead><tr><th>Benchmark</th><th class=n>Rate</th><th>Source</th></tr></thead><tbody>
    <tr class=hi><td>Clear Pool Solutions Tucson, real leads</td><td class=n>{pct(won, leads)}</td><td class=src>This report</td></tr>
    {bench}
  </tbody></table>
</section>

<section class="page-break">
  <h2>Leads and new customers by month</h2>
  <div class="legend"><span><span class="sw" style="background:var(--lead)"></span>Real leads</span><span><span class="sw" style="background:var(--won)"></span>Became customers</span></div>
  {chart(months)}
  <p class="foot">Bars are labelled customers / leads, by the month the lead first came in. *October is a partial month (to Oct 27). Summer
  (June – August) is the busy season, with August the strongest month: {by_month['2026-08']['won']} new customers from {by_month['2026-08']['leads']} leads.</p>
</section>

<div class="two">
<section>
  <h2>By month</h2>
  <table><thead><tr><th>Month</th><th class=n>Leads</th><th class=n>Customers</th><th class=n>Rate</th><th class=n>Spam</th></tr></thead><tbody>{month_rows}</tbody></table>
</section>
<section>
  <h2>By where the lead came from</h2>
  <table><thead><tr><th>Source</th><th class=n>Leads</th><th class=n>Customers</th><th class=n>Rate</th><th class=n>Spam</th></tr></thead><tbody>{src_rows}</tbody></table>
  <p class="foot">Google Ads = the Google Ads phone line, texts and landing-page form. Website &amp; Google Business = the website / Google
  Business Profile line, texts and site forms. Search-ad leads typically convert lower than calls from people who already found you
  (7.3% for search-ad leads across industries, per LocaliQ), so {pct(by_src['Google Ads']['won'], by_src['Google Ads']['leads'])} on Google Ads is a strong result.</p>
</section>
</div>

<section>
  <h2>Calls: what we found and fixed</h2>
  <p>From {CALLS['window']}, your lines received <b>{CALLS['total']}</b> calls: {CALLS['answered']} answered, {CALLS['not_answered']} not answered, and
  {CALLS['menu']} hung up during the "press 1" phone menu. Across home services, only about half of callers reach a person (Invoca), so this
  is common, but those callers were getting no follow-up at all. As of October 27:</p>
  <ul>
    <li>Every call now rings you directly (the "press 1" menu is gone).</li>
    <li>Every missed call gets an automatic "sorry we missed your call" text (once a day at most), a card in New Lead and a call-back task for you.</li>
    <li>Spam numbers and current customers no longer create new-lead cards; voicemail detection, which marked some answered calls as voicemail, is off.</li>
  </ul>
  <p>These are the leads most likely to move your rate up from November on.</p>
</section>

<section>
  <h2>Your GHL dashboard from November</h2>
  <div class="callout">
  <p><b>From November 1, the GHL dashboards show your numbers exactly as you asked:</b> only leads you can still contact stay "open",
  everything else is handled on its own: Lost cards stay as lost at $0, and Spam and Out of Scope cards are removed. Values are set
  automatically: open leads ${WEEKLY:,} (a weekly customer's average), weekly customers ${WEEKLY:,}, one-time repairs ${REPAIR}.</p>
  <p>Pipeline value today: <b>${won_value:,}</b> won ({WON_WEEKLY} weekly customers at ${WEEKLY:,}, {WON_REPAIR} one-time repairs at ${REPAIR})
  and <b>${OPEN_NOW * WEEKLY:,}</b> in open leads ({OPEN_NOW} at ${WEEKLY:,}). In the dashboard, set the date range to "Till date"
  to see these totals.</p>
  <p style="margin:0">For April – October, use this report rather than the GHL date filters. An old automation was deleting every card moved to
  Won; we stopped it and restored the {won} customer cards on October 27, and the statuses and values were also corrected that day. So in
  GHL those months show the cleanup date instead of when things really happened. The counts in this report come from your contacts, which
  were never affected.</p>
  </div>
</section>

<section>
  <h2>Everything we changed on October 27</h2>
  <ul>
    <li><b>Won customers:</b> stopped the automation that deleted Won cards and restored the {won} missing cards (no emails sent to customers).</li>
    <li><b>Calls:</b> direct ring, missed-call text and task, spam and customer filtering, voicemail detection off.</li>
    <li><b>Pipeline:</b> removed 2 empty stages; status and value set automatically by stage (open and weekly ${WEEKLY:,}, one-time repair ${REPAIR}, lost $0); spam and out-of-area cards removed.</li>
    <li><b>Dashboards:</b> removed 7 duplicate dashboards; three remain: Dashboard, Call Tracking and Lead Attribution.</li>
  </ul>
  <p>One habit keeps the numbers accurate: when a lead becomes a customer, move the card to Won; when it is a no, move it to Lost.</p>
</section>

<section>
  <h2>How the numbers are counted</h2>
  <ul class="foot">
    <li>Lead: a contact our automations tagged as a new lead from a call, text or form on one of the tracked lines. Existing customers who call are not counted.</li>
    <li>Spam: contacts tagged spam / do-not-disturb ({spam} in total), shown separately and left out of the real-lead rate. The contacts stay in your CRM; only their pipeline cards were removed.</li>
    <li>Customer value: ${WEEKLY:,} per weekly-service customer and ${REPAIR} per one-time repair, the averages you set.</li>
    <li>Customer: a lead whose card was moved to a Won stage (Won Customer or One Time Repair). Leads whose card was never updated count as not won.</li>
    <li>Data from your GHL account, April 1 – October 27, 2026. Benchmarks come from third-party industry reports and measure similar, not identical, steps of the sale.</li>
  </ul>
</section>
</body></html>"""
    OUT.mkdir(parents=True, exist_ok=True)
    page = OUT / "clear-pool-tucson-lead-report.html"
    page.write_text(html)
    pdf = OUT / "Clear Pool Solutions Tucson - Lead Report (Apr-Oct 2026).pdf"
    subprocess.run([CHROMIUM, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=10000", f"--print-to-pdf={pdf}", page.as_uri()], capture_output=True, timeout=180)
    print(pdf, pdf.stat().st_size // 1024, "KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
