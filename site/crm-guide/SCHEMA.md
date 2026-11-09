# CRM guide — data file schema (`site/crm-guide/data/<slug>.json`)

One interactive page (`site/crm-guide/index.html`) serves every client; only this JSON changes. Built by
`scripts/pp_crm_guide.py <slug>` from the V9 model (master "Snapshot Pool Profits" dump) with the client's own values.

```jsonc
{
  "version": 1,
  "generated_at": "2026-11-09",
  "client": {
    "slug": "corolla-pool-and-spa",
    "name": "Corolla Pool and Spa",          // friendly business name (custom value)
    "owner_first": "Josh",                  // representative / owner first name
    "business_phone": "(252) 573-3101",
    "city": "Corolla, NC",
    "location_id": "hhXkAONzl78btBsxb35f"
  },
  "prepared_by": "Pedro Garrido · Pool Profits",
  "meeting_note": "short sentence shown at the top (what this meeting is for)",

  // 6–8 plain steps of the lead → customer journey (animated timeline on the page)
  "journey": [
    {"id": "new", "icon": "phone|form|chat|clock|quote|calendar|trophy|star|refresh",
     "title": "A new lead reaches you", "text": "plain sentence", "stage": "new-lead"}
  ],

  // pipeline columns as the client sees them on the lead board, in order
  "pipeline": [{"id": "new-lead", "name": "New Lead", "plain": "what this column means", "auto": true}],

  // every message a CUSTOMER can receive, grouped by stage id (same ids as journey/pipeline where possible)
  "stages": [
    {"id": "missed", "title": "When you miss a call", "trigger_plain": "Someone calls and nobody answers",
     "messages": [
       {"code": "M1", "channel": "sms|email", "when": "Right away", "subject": "(email only)",
        "text": "exact text with real values filled in; contact fields as [First name]",
        "editable": true}
     ]}
  ],

  // what goes to the client's TEAM (alerts/tasks), plain list
  "team_alerts": [{"when": "A new lead fills your form", "what": "Text + email with name, phone, service", "who": "Josh"}],

  // the client's part, per project area — rendered as a checklist with "Done" / "Need help" + note
  "client_tasks": [
    {"id": "t-phone", "area": "Phone|Google|Website|Team|Messages|Billing|Other",
     "title": "Pick the phone that should ring for new leads",
     "why": "one sentence",
     "steps": ["step 1", "step 2"],
     "status_hint": "todo|done|na"        // from the live account (e.g. Google already connected → done)
    }
  ],

  // yes/no questions for the meeting
  "decisions": [{"id": "d-reentry", "question": "...", "suggestion": "..."}]
}
```

## Publicar (padrão para todo cliente novo, antes do go-live)
1. `scripts/pp_crm_guide.py <slug>` → `site/crm-guide/data/<slug>.json` (revisar).
2. `scripts/pp_crm_guide_site.sh <slug> "<Nome curto>" <scratchpad>/crm-guide/<slug>`.
3. Artifact: `file_path` = `index.html` da pasta, `files` `{data.json, logo.png}`, `capabilities {db:{}, user:{}}`,
   icon `guide`. Republicar a mesma pasta mantém a URL.
4. Compartilhar: convidar o e-mail do cliente como **Editor** (Share) → as respostas gravam no `db`; sem convite elas
   ficam no navegador dele e o botão "Copy my answers" gera o texto para colar no Basecamp.
5. Depois da reunião: ler `edits`, `tasks`, `answers` com ArtifactData e aplicar (`config/<cliente>_wording.json`).

Publicados (09/11): Corolla https://claude.ai/artifact/Mssjgf1bDYimNqcHpJdp8W · Aqua Clear
https://claude.ai/artifact/Lvjw8puELksVQ71xV4TCcN

Page state (claude.ai artifact `db`, read back with ArtifactData):
- `edits/<code>`: `{code, status: "ok"|"change", new_text, note, by, at}`
- `tasks/<id>`: `{id, status: "done"|"help", note, by, at}`
- `answers/<id>`: `{id, answer: "yes"|"no", note, by, at}`
