# Prompt 2 para a extensão do Chrome (13/11 tarde) — postar o que foi aprovado (A1–A8) + nova passada no inbox + o que está aberto

```
Same job as before: you are me, Pedro Garrido, in my browser. Same rules as the first pass (first person "I", never "we", never mention Claude/AI/automation, English to the team and clients, "Pool Profits CRM" instead of GHL/GoHighLevel to clients, 5-minute rule, reactions only now and then, no changes inside GoHighLevel or n8n, nothing deleted/archived, no task statuses changed). Nothing a client sees goes out unless it is listed below as APPROVED.

PART A — POST THESE (already reviewed and approved by me)

A1. ClickUp, task "Old-snapshot accounts → decide V9 migration (Pool Palooza, Corolla, Aqua Clear, ABC, Clear Conceptz, Pool Smart OC…)" (https://app.clickup.com/t/86bcz86jw). Add this comment:
"Clear Conceptz cleaned up (backup of every copy kept). The account had 2 'Pool Leads' pipelines from two old snapshot loads and 3 published copies of 5 flows. Moved to draft: the 3 copies of Current Customer / DND Contact / Review Request that listened to a pipeline that no longer exists (they could never run), the 2 extra 'Incoming Call To Pipeline' copies (all 3 listened to the same old number), and the 2 extra 'Website Form Fill To Pipeline' copies that fired on the same tag as the main one (a lead got the card, alert and task up to 3 times). Still live: 1 Website Form Fill, 1 Incoming Call, and 1 copy of Current Customer / DND / Review Request per pipeline. Next for this account: the form alerts have no user picked, so they reach nobody; I'll check with Frank who should get them."

A2. Gmail, thread "GoHighLevel Automation Ideas for Lead Tracking & Client Accountability" (Frank, Val, Ed in copy). Reply all:
"Hi Frank and Val,
Here's what I can do for each idea:
1. Cards stuck in a stage (Frank): this one is native. A workflow in each account alerts the team when a card sits in the same stage for 3, 4 or 5 days. I'd add it to the snapshot so every account gets it.
2. One place for all accounts (Frank and Val): I can send a summary every 3 days, by email or in a ClickUp channel, covering every Google Ads client: new leads by source, how many were contacted, quoted and won, which cards are stuck and which leads got no follow-up. I pull it from all the sub-accounts at once, so nobody has to open each one.
3. Ad spend, CPL and branded PDF reports (Val): spend lives in Google Ads, not in the CRM. Two ways: add spend to the same summary by pulling it from Google Ads (needs Val's access set up once), or use an outside reporting tool (Looker Studio is free; AgencyAnalytics or DashThis are paid and do branded PDFs).
I'd start with 1 and 2, then decide 3 together. Does that order work for you?
Pedro"

A3. Google Calendar / Gmail: accept Ed's invitation "Pool Duck CRM Review" (Monday Nov 16, 5:15–6:15 PM Brasília = 2:15–3:15 PM CST). Click "Yes" in the invite email or in Calendar.

A4. Basecamp check-ins (client-visible, APPROVED by me). Basecamp was in read-only mode earlier. Try now: if posting works, post each as a NEW message (Message Board → New message, title "Quick check-in") in the right project; if Basecamp still says read-only, don't post and tell me in the report.
- Project "Precision Pools & Landscape":
  "Hi Dane, quick check-in from my side. 38 new leads came in this week and every one landed in your pipeline with its source and the follow-up texts. How is the lead flow working for you and the team? Anything you'd like changed in the texts or the alerts?
  Pedro"
- Project "Sunwave Pool Pros":
  "Hi Davey, I saw you made some changes to your phone menus on Wednesday. Is everything ringing the way you want? If you'd like, I can double-check the menu or adjust where each line goes. Also, 21 new leads came in this week, all with a card in the pipeline. Anything you'd like to adjust?
  Pedro"
- Project "Bahama Blue Pool & Spa":
  "Hi Andy, checking in. Missed calls now get the follow-up text automatically, and your 28 customers are in the system tagged as existing customers, so they don't get new-lead messages. How is it working on your end? Anything you'd like to change?
  Pedro"

A5. ClickUp DM with Frank (https://app.clickup.com/90141148207/chat/r/2kyd9h1f-1154), reply to his message about the Skimmer native integration (APPROVED):
"Went through the Skimmer doc. The native add-on is the best fit for clients who want leads in both systems, and it doesn't need Enterprise. My standard setup: keep our CRM form on the site so every lead gets the alert, card and follow-up texts; in Skimmer turn on only Lead conversion (when the card reaches Won, Skimmer creates the customer and service location), the daily Skimmer-to-CRM customer sync, and activity notes; leave Initial contact sync and Contact update sync off, or every lead and old contact becomes a Skimmer customer. The client buys the add-on in Skimmer, and I create the token in their sub-account. Matching is by email only, so leads without an email won't link, and I'll make sure customers coming from Skimmer never get new-lead messages. I'll test it on one account before we offer it to Nathan. OK to go with this as the standard?"

A6. Basecamp, project "The Pool Keepers", thread "Automations – Review" (client-visible, APPROVED). Post only after A5 is sent and only if Basecamp lets you post. This REPLACES the older Nathan draft in the email "[Aprovar] Pool Keepers…" (don't post that old one):
"Hi Nathan, thanks for sending the Skimmer form. Good news: Skimmer now connects directly to your Pool Profits CRM as a monthly add-on, no Enterprise plan needed. Here's how I'd set it up so every lead lands in both places without double entry: your website keeps the current form, so new leads go straight into your CRM with the team alert, the pipeline card and the follow-up texts; when a lead becomes a customer, Skimmer creates the customer and service location automatically; and Skimmer sends customer updates and service notes back to the CRM every day. To turn it on, the CRM integration needs to be added in your Skimmer account (Integrations Center; Skimmer shows the monthly price there). Once it's added, I'll connect it, test it end to end and let you know before anything changes. Until then I'd keep the current website form live so no leads get missed.
Pedro"

A7. ClickUp task "Pools of Perfection – basic sub-account with V9 snapshot (no A2P)" (https://app.clickup.com/t/86bd2p4gc). Add this comment (don't change the status):
"Sub-account created with the V9 snapshot (America/New_York) and the full model setup: pipeline, forms, workflows, standard dashboard, business info and Business Profile filled (Pools of Perfection of Armonk Inc., rep Christopher Carthy, CEO). Christopher is a user (admin) and gets every lead alert and task; he logs in with "Forgot password" at app.poolprofits.com. Audit: 0 issues. Native missed-call text off. Still open: no phone number and no A2P on purpose; Review Request stays in draft until we have his Google review link; the CRM guide goes out with the next daily round."

A8. Basecamp, project "Pools Of Perfection", thread "✨ Business Info Internal" (team only), reply to Frank:
"Frank, the Pools of Perfection sub-account is set up (V9, lead alerts to Christopher, no number/A2P yet). One thing to confirm with him: his questionnaire gave (516) 458-4031 as the business phone, while the Armonk store is (914) 273-7946. The texts show the business phone, so which one should customers see? Also, if you have his Google Business Profile link, send it over and I'll turn on the review requests."
If Basecamp is still read-only, post A8 as a ClickUp DM to Frank instead.

PART B — NEW PASS ON THE INBOX AND WHAT IS STILL OPEN
Check Gmail, ClickUp (Inbox, DMs with Frank / Val / "Pool Profits" (Ed), group DM, task comments mentioning me) and Basecamp ("Hey!" menu) for anything that arrived after your first pass, or that you couldn't open then (the 3 threads in Frank's DM from yesterday: Reign moving old leads, NorTex setup, Passion spam leads — try opening them again). Handle them the same way as the first pass: answer simple team items, show me client-visible drafts, and put anything that needs CRM work in the report with the full text.
Also look for answers from Frank to these two questions I asked him in DM: (1) did Pool Time, Reign or Sparkling Clear ask for the "free month for referrals" offer; (2) does Brett (Southern) delete pipeline cards. Copy his answers word for word into the report.
Also check and report the current state of these open items (just look, don't act unless it's a simple team reply):
- ClickUp task "Bonneville – format client list for GHL import" (https://app.clickup.com/t/86bcz0y7b): is the file "Customers (4).xlsx" attached now? If yes, give me the attachment name and date.
- ClickUp task "Live tests with Pedro – all pending (one list)" (https://app.clickup.com/t/86bd1b3b5): any new comments.
- ClickUp task "Dashboards: reconnect expired Ads integrations + fix GA access" (https://app.clickup.com/t/86bd1zk8p): did Val say which accounts she reconnected?
- Gmail: any answer from Matt (Pool Duck Odessa) to "Your prices for the Pool Duck Odessa follow-up texts"; any new email from Atif, Val, Frank or Ed.

REPORT (Portuguese, same 4 sections: RESPONDIDO / AGUARDANDO O PEDRO / PARA O CLAUDE FAZER NO GHL / NÃO CONSEGUI), including whether each of A1–A8 was posted.
```
