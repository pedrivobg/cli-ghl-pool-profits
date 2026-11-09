# Revisão de conta nova (quando o Pedro diz "conta pronta para revisão")

Rotina do inbox segue isto. Base: Bonneville (02/11), West Coast + Capital (09/11). Sem `pp_e2e`, sem mensagem a cliente.
`P` = `./.venv/bin/python scripts`. `<n>` = parte do nome da sub-conta; `<loc>` = id.

## 0. Pré-condição (passo do Pedro)
- [ ] E-mail "Nova subconta criada: <nome> - Falta 1 passo" lido e form do n8n enviado (custom values preenchidos:
      `owner_first_name`, `logo_url`, `google_review_link`…). Se estão vazios → responder "aguardando o passo do form".
- [ ] Survey: `GET services /surveys/submissions?locationId=wohRifObKPEykgu17LJu` → a submissão do form
      `efErcbOr4GAKXzZ28J4S` (ignorar a de outro `formId`) com o e-mail/empresa da conta.

## 1. Dados e ajustes básicos
```
P/pp_dump.py --only "<n>" --only "Southern Pool"
P/pp_onboarding_fill.py --submission <sub> --loc <loc> --timezone [--apply]     # 'null' → vazio, fuso Sao_Paulo → cliente
```
- [ ] Custom values (GET + backup, PUT `/locations/<loc>/customValues/<id>`): Friendly Business Name = nome do site/GBP
      (legal fica no legal); Service Area curta (cidade/região, não o texto do survey); `a2p_verification_number` = número
      do GHL (sem número: telefone do negócio, provisório).
- [ ] `PUT services /locations/<loc> {enableMissedCallText: false}`.
- [ ] Usuário = representante do Business Profile (`authorizedRepresentative`). Sem usuário: `P/pp_add_user.py --loc <loc>
      --like-loc <outra conta> --like <admin dela> --first … --last … --email … --phone …` (permissões de um admin) e o
      representante via `PUT /locations/<loc> {authorizedRepresentative}`.

## 2. Modelo
```
P/pp_dump.py --only "<n>";  P/pp_mirror.py --target "<n>" [--apply]
P/pp_forms.py --only "<n>" [--apply];  P/pp_nps.py --only "<n>" [--apply]
P/pp_dump.py --only "<n>"                                    # sempre depois do pp_nps (lição Bonneville)
P/pp_fix.py --only "<n>" --drop-booking --include-drafts --skip "In Communication Stage" [--apply]
P/pp_tags_missing.py --only "<n>" [--apply]                  # "✗ faltam" logo após criar = leitura atrasada: rodar de novo
P/pp_skip_tag.py --only "<n>" [--apply];  P/pp_line_tag.py --only "<n>" [--apply]   # sem número: nada a fazer
P/pp_master_cleanup.py --loc <loc> [--apply]                 # Sequential Call Routing genérico + gatilhos de outros clientes fora
P/pp_review_fix.py --only "<n>" [--apply]
```
Sem Google conectado: o link de review vem do `google_review_link` (g.page/…/review resolve o place). `share.google/…`
não resolve → Review Request fica draft até conectar o GBP (depois: `pp_dump` + `pp_mirror --apply`).

## 3. Conferir (só leitura)
- [ ] Telefones: `GET services /phone-system/numbers/location/<loc>` ("No Twilio account" = LC Phone não ativado;
      `forwardingNumber` de cada número — não há API para gravar: passo de tela).
- [ ] A2P: site com privacy/terms? (404 → funil "New A2P Verification" num subdomínio). Status só na tela (Trust Center).
- [ ] Usuários: primeiro acesso por "Forgot password" em app.poolprofits.com; telefone no usuário (recebe os SMS internos).
- [ ] Calendários: com membros, ou booking tirado (`--drop-booking`; inativos sem membros = padrão).
- [ ] Funis "Simple Pool Care"/"LP Teste" do snapshot antigo: não mexer (Bonneville igual).
- [ ] Teste seguro: contato `ZZ TEST` @example.com sem telefone/tags → "Contact Created → add owner" atribui o
      representante; apagar o contato.
```
P/pp_dump.py --only "<n>";  P/pp_audit.py --only "<n>";  P/pp_ready.py --only "<n>" [--place <slug>=<placeId>]
```

## 4. Guia do CRM (todo cliente, antes da pre-meeting do go-live)
Página interativa padrão hospedada no n8n (mesmo layout para todos, só os dados do cliente mudam):
```
P/pp_crm_guide.py <slug>            # revisar site/crm-guide/data/<slug>.json
P/pp_crm_guide_publish.py <slug>    # CRM_GUIDE_ADMIN_KEY no env → imprime o link público
```
Link → Frank (ClickUp DM) → cliente. As respostas gravam sozinhas (tabela n8n "CRM Guide Answers") e o "Send to Pedro"
avisa por e-mail; eu aplico os textos (`config/<cliente>_wording.json`) e as tarefas dele viram itens do onboarding.
Detalhes: `site/crm-guide/SCHEMA.md`.

## Pronto quando…
- `pp_audit` **0 ALTA** (as 4 MÉDIA "Add Task incompleto" + Won/Review mesmo gatilho existem no modelo);
- `pp_ready` **0 ERRO** (aviso aceito: Review Request draft sem place);
- fuso do cliente, missed-call nativo off, nenhum `null`, representante = usuário, dono do contato testado;
- log em `docs/execucao-*.md` e passos de tela do Pedro (número + encaminhamento, LC Phone, A2P, GBP, primeiro acesso,
  ligação de teste) numerados no relatório e no `docs/TODO.md`. "Pronto para começar" só depois do número + A2P.
