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

## Publicar (padrão para todo cliente novo, antes do go-live) — hospedado no n8n, link público automático
1. `scripts/pp_crm_guide.py <slug>` → `site/crm-guide/data/<slug>.json` (revisar).
2. `CRM_GUIDE_ADMIN_KEY=… scripts/pp_crm_guide_publish.py <slug>` → imprime o link
   `https://n8n.valenteai.cloud/webhook/crm-guide?c=<key>` (guardado em `config/crm_guide_links.json`; republicar
   mantém o link e as respostas). Mudou o layout (`index.html`/logo) → `pp_crm_guide_publish.py --template` (vale para
   todos os clientes na hora). A chave de admin está no nó "Check admin key" do workflow n8n
   `SlfpWZmKH1d62hB9` (nunca no repo).
3. Mandar o link ao Frank (ClickUp DM); ele envia ao cliente. Ninguém precisa mexer em compartilhamento.
4. O cliente responde na própria página: cada clique grava na tabela n8n "CRM Guide Answers" (`tju295LzOR6tfp8J`,
   uma linha por key/kind/item_id; `payload` = JSON) e volta na próxima visita, em qualquer aparelho. "Send to Pedro"
   manda o resumo por e-mail para pedro@ (cc Frank). "Copy my answers" continua como reserva.
5. Aplicar: ler as linhas da key (`get_data_table_rows`) → textos em `config/<cliente>_wording.json`, tarefas dele →
   onboarding. Apagar uma resposta de teste = POST `crm-guide-answer` com `body: {}` no mesmo item.

Publicados (09/11): ver `config/crm_guide_links.json`.

Answer payloads (`kind` / `item_id` → `payload`):
- `edits` / `<code>`: `{code, status: "ok"|"change", new_text, note, at}`
- `tasks` / `<id>`: `{id, status: "done"|"help", note, at}`
- `answers` / `<id>`: `{id, answer: "yes"|"no", note, at}`
- `submit` / `final`: `{summary, at}` (texto do resumo, também vai por e-mail)
