# E-mail para Ed, Frank e Jonathan: novo processo automático de conta nova (Pedro 10/11)

**Enviar só quando TODAS as condições abaixo estiverem verdadeiras** (a rodada diária confere e envia; depois marca aqui
"Enviado em <data>" e fecha a tarefa do ClickUp):
1. Um A2P enviado pelo fluxo automático (`pp_new_account.py --submit`) com brand e campanha aceitos (status ≠ pending/failed
   em `pp_a2p.py status`). Hoje: Corolla espera o SSL do go.corollapoolandspa.com; Smart Chem, West Coast, Capital,
   Rosebrook, WP Pools e Bonneville esperam o 1º número (KYC).
2. Guia do CRM enviado automaticamente a um cliente real (`config/crm_guide_email.json` com `approved: true`).
3. Usuário do dono criado automaticamente numa conta nova real (passo 2b do `pp_new_account.py`; testado na Test Snapshot
   10/11).
4. Snapshot V9 com Refresh feito pelo Pedro (dashboard padrão + gate de nota dentro).
Se algo mudar no processo antes do envio, ajustar o texto.

Para: sales@poolprofits.com (Ed), frank@poolprofits.com, web@streamlineresults.com (Jonathan). De: Pedro.

---

**Subject:** New client onboarding is now automatic (GHL account, users, CRM guide, A2P)

Hi Ed, Frank and Jonathan,

The new-client setup in GHL now runs on its own. Here's how it works from now on:

1. **The client fills out the onboarding questionnaire** (Local SEO Onboarding Form 2.0). That creates their GHL sub-account from the current snapshot, with the full automation system, the standard dashboard from our meeting and the review rating (only 5 stars get the Google review link; anything below gets a "what could we have done better" text and alerts the owner).
2. **Every business day, I go through the new accounts automatically**:
   - business info, time zone and custom values filled in from the questionnaire;
   - the owner added as a user (they get in with "Forgot password" at app.poolprofits.com);
   - the A2P business profile filled in;
   - the phone lines bought, named (Website & GBP, Google Ads, Facebook Ads) and forwarded to their business phone;
   - a full check against the snapshot.
3. **The CRM guide goes straight to the client** before the pre-launch meeting. They approve or change every message on the page, and their answers come back to me automatically.
4. **As soon as the domain is connected** (the client points go.<their domain> and the A2P site loads), the A2P registration is submitted automatically, following our SOP. An AI compliance check runs first, so we don't pay for submissions that would be rejected.

What's still manual:
- the first phone number of each account (GHL asks for an ID check once); I take care of that;
- the client's DNS record, and Frank connecting the domain to the A2P site;
- the client's first login.

How this helps us:
- a new client gets set up much faster, with no back-and-forth;
- every account is on the same current setup, so no more old snapshots like the Corolla case;
- A2P goes out right the first time;
- Frank no longer chases the guide or the paperwork.

I've already tested all of it on real accounts. If you have any questions, let me know.

Thanks,
Pedro
