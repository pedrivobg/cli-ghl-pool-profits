# Conta nova: processo completo (automático desde 10/11)

Rotina do inbox segue isto. Base: Bonneville (02/11), West Coast + Capital (09/11). Sem `pp_e2e`, sem mensagem a cliente.
`P` = `./.venv/bin/python scripts`. `<n>` = parte do nome da sub-conta; `<loc>` = id.

## 0. Pré-condiç## 0. Automático (sem private key, sem form do n8n)
```
P/pp_new_account.py -n "<n>"            # plano: survey, perfil A2P, telefone, site A2P, status
P/pp_new_account.py -n "<n>" --apply [--submit]   # --submit envia o A2P quando tudo está pronto (pago)
P/pp_new_account.py --scan --apply --submit       # todas as contas dos últimos 30 dias (rodada diária, abaixo)
```
- Survey casado por e-mail/nome; custom values só em conta "fresca" (fuso Sao_Paulo ou Friendly Name vazio) — nunca
  sobrescreve texto editado à mão. Perfil A2P só nos campos vazios (padrão CONSUMER / CEO / USA_AND_CANADA).
- Telefone: a **1ª compra de número** da sub-conta pede verificação de identidade do GHL (Persona, `GUARD_LOCATION_NOT_KYC_VERIFIED`)
  → passo do Pedro/Frank uma vez; depois o script compra (DDD do telefone do negócio) e encaminha para o telefone do negócio
  (`POST backend /phone-system/twilio-accounts?locationId= {number, forwardingNumber}`).
- A2P: o site "New A2P Verification" precisa do domínio go.<domínio> (Frank conecta; cliente cria o CNAME). Quando
  `/pools/privacy-policy` e `/pools/terms-of-use` carregam → custom values privacy/terms + campanha + envio.
- Questionário não respondido (tarefa "update required", sem sub-conta) → nada a fazer.

ustes básicos
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
- [ ] Telefones e A2P: `P/pp_a2p.py status -n "<n>"` (números, encaminhamento, perfil, campanha, brand/campaign status).
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
- guia do CRM publicado e link com o Frank; comentário na tarefa "Create GHL Account For Client <nome>" (fechar só
  quando número encaminhado + A2P enviado + guia enviado);
- log em `docs/execucao-*.md`; passos humanos restantes (1º número, DNS, GBP, primeiro acesso) num e-mail "[Passo seu]".

## Rodada diaria (item "daily-newaccounts-<data>" do n8n, 1x por dia útil a partir das 9h BRT, rotina "GHL Tasks")
O n8n (Pedro Inbox Watch, nó "Daily new-accounts item") manda esse item uma vez por dia; não existe rotina separada.
1. Chave do guia do CRM: ler do workflow n8n `SlfpWZmKH1d62hB9`, nó "Check admin key", e exportar `CRM_GUIDE_ADMIN_KEY` só no
   shell (nunca imprimir/gravar/commitar).
2. `P/pp_new_account.py --scan` (ler o plano) → `P/pp_new_account.py --scan --apply --submit`.
3. Toda sub-conta criada nos últimos 30 dias: `pp_dump` + `pp_audit` + `pp_ready`. Sem a sequência do modelo (sem os workflows
   V9, ALTA no audit ou ERRO no ready) → seções 1–3 acima completas (usuário = representante em todo aviso/tarefa).
4. Guia do CRM: conta sem entrada em `config/crm_guide_links.json` e com o passo 3 ok → `pp_crm_guide.py` + conferir o JSON +
   `pp_crm_guide_publish.py` + abrir o link → DM ao Frank (ClickUp, user 94490678) com o link.
5. ClickUp, lista `901417290241`: tarefa "Create GHL Account For Client <nome>" (casar pelo nome; Smart Chem ficou na
   86bcywax9 da lista do Pedro). Um comentário só quando algo mudou desde o último (feito / esperando: Frank conectar
   go.<domínio> ao site "New A2P Verification" + CNAME do cliente; Pedro: 1º número; status do A2P). Fechar só com: audit
   limpo, usuário nos avisos/tarefas, número encaminhado, A2P enviado, guia enviado. Tarefa sem sub-conta (questionário 2.0
   "Local SEO Onboarding Form 2.0" = `efErcbOr4GAKXzZ28J4S` não respondido) fica como está — o "Pool Profits Training Survey
   Intake Form" (`4irAGdK9ycRh4itHvI8C`) NÃO cria sub-conta.
6. Algo que precisa do Pedro (1º número, passo travado) → UM e-mail "[Passo seu] Contas novas <data>". Nada → sem e-mail.
7. Registrar em `docs/execucao-*.md`, commit/push só se mudou arquivo. Marcar o item `done` no ledger.

