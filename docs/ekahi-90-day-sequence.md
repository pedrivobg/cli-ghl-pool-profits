# Ekahi Solutions: "First 90 Days" sequence (for Frank's review)

Account: Ekahi Solutions LLC (Honolulu, Erik). Approved by Frank (e-mail 06/11/2026): pause the monthly reminder,
build the first-90-days sequence in **draft**. Erik already uses Skimmer and sends visit reports, so this sequence
sends no visit reports.

- Workflow: **First 90 Days - New Client Sequence** (DRAFT, folder "04 Pipeline Automations"). Script:
  `scripts/ek_90day.py` (`pause` / `build [--apply]` / `test`).
- Trigger: card moved to **Pool Leads / Won**, the same trigger as Won Stage, Post-Appointment Follow-up and Review
  Request. Re-entry off: moving the card to Won again later does not restart the sequence.
- Every message waits for Mon-Fri 9:00-17:00 Hawaii time (account time zone Pacific/Honolulu).
- Before every message: "Still a client?" check. Contacts tagged `lost lead`, `spam`, `dnd` or `one-time customer`
  leave the sequence. Contacts who texted STOP are skipped by GHL anyway (DND).
- `{{custom_values.business_phone}}` prints as +1 808-754-5907, `{{custom_values.friendly_business_name}}` as
  "Ekahi Solutions".
- **Monthly Service Reminder: paused (draft) on 07/11/2026**, backup in `backup/ekahi-solutions-llc/`.

## The texts

| When | Channel | Template | Text |
|---|---|---|---|
| Won + 2 min | SMS | (existing, Won Stage, unchanged) | Aloha {{contact.first_name}}! Welcome to Ekahi Solutions! 🏊 We're excited to have you on board. Your first service will be scheduled shortly. Questions? Call us at {{custom_values.business_phone}} |
| Won + 1 h (Day 1) | SMS | 90 Days - Day 1 - Service Details | Aloha {{contact.first_name}}, Erik here from Ekahi Solutions! A few quick things so your first visit goes smooth: Any gate code or lockbox? Any pets we should know about? Best way to reach you, text or call? Just reply here. Mahalo! |
| Day 7 | SMS | 90 Days - Day 7 - First Visit Check-in | Howzit {{contact.first_name}}! How was your first visit? Anything we should know about your pool or equipment? Just reply here or call/text +1 808-754-5907. - Erik, Ekahi Solutions |
| Day 14 | SMS | (existing, Review Request, unchanged) | NPS rating request, then Google review link for happy clients / alert to the team for unhappy ones |
| Day 30 | SMS | 90 Days - Day 30 - Island Pool Tip | Aloha {{contact.first_name}}! Quick tip from Erik: heavy rain dilutes your chemicals and strong sun burns off chlorine, so if the water looks off after a storm or a hot week, let me know. When the trade winds kick up, keeping the skimmer basket clear helps a lot. Reply anytime! Reply STOP to opt out. |
| Day 75 | E-mail | 90 Days - Day 75 - Filter Clean Heads-up | Subject: Your filter cleaning is coming up soon. "Aloha {{contact.first_name}}, It's been about 75 days since you started your service with Ekahi Solutions, which means your filter cleaning is coming up soon! We'll be keeping an eye on it during our next few visits and will get you scheduled when the cleaning is due. As always, if you have any questions or concerns about your pool, just reply to this email or call/text us at +1 808-754-5907. Mahalo, Erik, Ekahi Solutions, +1 808-754-5907" (same text as the draft "Filter Clean Reminder", with Aloha and reply/call/text) |
| Day 165, then every 90 days | SMS | 90 Days - Quarterly Seasonal Check-in | Howzit {{contact.first_name}}! Seasonal check-in from Erik at Ekahi Solutions: anything new with your pool? More swimming, guests coming, equipment making noise? Just reply or call/text +1 808-754-5907. Mahalo! Reply STOP to opt out. |

No booking links anywhere. "Reply STOP to opt out" only on the two non-service messages (Day 30, quarterly).

## What changes when it is published (not done yet)

1. Publish **First 90 Days - New Client Sequence**.
2. **Post-Appointment Follow-up** (published): its "SMS 1" (1 h after Won, "How did everything go with your pool
   service today?") is replaced by the Day 1 / Day 7 texts above. Remove that SMS and change the "wait for reply to
   SMS 1, up to 2 days" step to a plain 2-day wait, so the tags (`service completed`, `review requested`) and the move
   to Recurring Customer keep working as today.
3. **Filter Clean Reminder** (draft) stays draft: Day 75 now lives in the new sequence.
4. **Monthly Service Reminder** stays draft (paused 07/11).

## Test (07/11/2026)

Copy "ZZ TEST First 90 Days - New Client Sequence" in the account with 1-minute waits, no time window and a tag in
place of each SMS/e-mail (nothing sent); test contact without phone (example.com e-mail). Results in
`docs/execucao-2026-10-27-clearpool-dash.md` (07/11). Copy and contact deleted afterwards.
