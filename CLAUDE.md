# Contexto para o Claude — cli-ghl-pool-profits

- Cliente/agência: **Pool Profits** (GHL de agência, nicho de limpeza de piscina nos EUA).
  Operador: Pedro. Snapshot atual: **V9** (guia: Implementation Guide v1.0, 25 workflows em 9 pastas).
- Base do CLI copiada de `pedrivobg/cli-ghl-ff` (Fórmula Fitness). Lá: 1 sub-conta, PIT.
  Aqui: **todas as sub-contas** via token Firebase de agência (`utils/agency.py`).
- Credencial: `GHL_FIREBASE_REFRESH_TOKEN` (env do ambiente ou `.env`). Nunca imprimir,
  logar ou commitar. `dump/`, `reports/`, `backup/` são dados de clientes — gitignored.
- Sub-conta **modelo**: Southern Pool + Outdoors. Prioritárias (calls com clientes):
  Passion Pool Care, Stay Fresh Pools, Bahama Blue Pool & Spa, The Pool Shack, The Pool Keepers
  (`config/priority.json`). Estado-alvo: `docs/modelo-southern.md`.
- Fluxo: `pp_dump.py --priority` → `pp_audit.py` → `pp_compare.py` → revisar → aplicar
  (`pp_mirror` → `pp_forms` → `pp_fix --drop-booking`). Histórico: `docs/execucao-*.md`;
  pendências do Pedro: `docs/TODO.md`.
- Conta nova (onboarding): `pp_onboarding_fill` (+ fuso) → custom values do GHL (`a2p_verification_number` = número
  do GHL, friendly name como no site) → `pp_mirror --apply` → `pp_forms` → `pp_nps` → `pp_fix --drop-booking
  [--include-drafts --skip "In Communication Stage"]` → `pp_tags_missing` → `pp_skip_tag` → `pp_line_tag` →
  missed-call nativo off → Sequential Call Routing draft → `pp_audit` + `pp_ready.py` (usuário = representante
  do Business Profile em todo aviso/tarefa). Sem Google conectado o link de review vem do `google_review_link`.
- Master do snapshot = sub-conta "Snapshot Pool Profits" (`Kvdj7o189zlS3caaCNuX`), no padrão Southern desde 22/10:
  mudou o modelo → `pp_mirror --apply --template` + a mesma sequência nela → Pedro clica Refresh no snapshot (não vai
  para o TODO). PDF do sistema para cliente (funis, funil de vendas, automações, todas as mensagens com código A#/M#):
  `pp_snapshot_guide.py --for "<cliente>"` (textos em `config/snapshot_guide.json`; nome novo de workflow → descrever lá).
  Revisão do que está NO AR numa conta (ativas, gatilho, tempos, texto real, resposta, próximo passo, linha do tempo
  simulada, decisões): `pp_automation_review.py <slug>` com `config/review/<slug>.json` (Ekahi, 22/10).
- **Testes são nossos** (Pedro, 19/10): para a equipe (Frank, Val, Ed) e os clientes, Pedro e o Claude são
  uma pessoa só. Nunca pedir a eles para testar; testar daqui e, o que precisar de mão humana (ligação,
  UI do GHL/Google Ads), passar o passo a passo para o Pedro. Mensagens para eles só depois de testado.
- Regras de escrita no GHL: sempre GET + backup em `backup/<slug>/<id>.json` antes de PUT;
  testar em 1 sub-conta e revisar o diff antes de aplicar no resto; não mudar lógica sem
  pedido — correções básicas (nome de outra empresa, custom value vazio, link morto,
  usuário faltando) e status draft/published conforme o modelo.
- Endpoints com mais de um caminho conhecido passam por `Agency.first_ok`; o caminho que
  funcionou aparece no fim do `pp_dump.py` — atualizar a ordem em `agency.py` se mudar.

## Comportamento da API do GHL (verificado ao vivo)

- Workflow PUT valida assets: id de pipeline/etapa/campo de outra location → 400
  `ASSET_VALIDATION_FAILED`. Leituras logo após escrita podem vir defasadas (pipeline,
  listagem pública de workflows, busca de contatos): reler com espera.
- Workflow PUT volta ao padrão toda configuração que o corpo não traz (`allowMultiple` = allow re-entry,
  `allowMultipleOpportunity`, `window`, `timezone`…): `Agency.call` completa com os valores atuais (20/10; antes
  disso 166 workflows perderam o re-entry — `pp_wf_settings.py`). Re-entry off = 2ª entrada ignorada (testado).
- Gatilho: `active` segue o status do workflow (draft → inativo); PUT não liga/desliga.
  Para tirar um gatilho: `DELETE /workflow/{loc}/trigger/{id}` (com backup).
- Pipeline: `PUT services /opportunities/pipelines/{id}` com `{name, stages}` (sem
  `locationId`); etapa sem `id` é criada; ids existentes preservados.
- Inbound webhook: gatilho `type: inbound_webhook`; URL
  `https://services.leadconnectorhq.com/hooks/{loc}/webhook-trigger/{triggerId}`; passo
  `create_update_contact` com `fields` em camelCase (`firstName`, `email`, `phone`,
  `address1`) e valores `{{inboundWebhookRequest.<campo>}}`.
- Missed-call text back nativo: `enableMissedCallText` via `PUT services /locations/{id}`.
- Submissão de form não automatizável (Turnstile no `/forms/submit`); testar gatilhos por
  tag/etapa (`pp_e2e.py`) e conferir submissões reais em `/forms/submissions`.
- SMS de workflow usam o template (`attributes.template_id`) — o texto vive no template;
  e-mail guarda cópia do html no passo **e** no template (corrigir os dois).
- Nunca rodar `pp_e2e.py` em conta de cliente (dispara mensagens e notificações reais).
- Filtro de gatilho por tag (formato da UI): `{"field": "contact.tags", "id": "doesnot-have-tag",
  "title": "Doesn't Have Tag", "type": "select", "operator": "index-of-false", "value": "<tag>"}`
  (Has Tag: `index-of-true`, id `has-tag`). Funciona em `pipeline_stage_updated`.
- Forms: ler `GET backend /forms/{id}`; gravar `POST backend /forms/{id}` com `{name, formData}`
  (sem `locationId`); criar `POST backend /forms/` (resposta `{"form": …}`). Campo customizado
  no form = `fields[].tag` com o id do custom field DA CONTA (snapshot traz id da origem).
  O `formData` do GET fica minutos defasado depois de gravar: o conteúdo real é o arquivo da versão mais nova
  (`versionHistory[].formDataDownloadUrl`) — ler dele antes de regravar, senão volta edição recente.
- Form → redirecionar: `formAction.actionType "1"` (`"2"` = mensagem) com **`redirectUrl` e `redirect_url`** (o widget
  lê `redirect_url`; só `redirectUrl` = redireciona para URL vazia = recarrega a página). O GET do form devolve só
  `redirectUrl`: GET → POST apaga o `redirect_url` (quebrou BluVantage 15/10 e Southern 16/10). Gravar sempre com
  `_common.keep_redirect(fd)`. Form **criado** (`POST /forms/`) com os dois campos também perde o `redirect_url`: regravar
  (`POST /forms/{id}`) depois — o form novo responde 404 ao POST por alguns minutos (GET funciona): tentar com espera
  (`nx_ads_forms.py`). Texto solto no form (aviso perto do botão) = campo `type: "h1"` com `label` em HTML (YardSpring/NorTex 27/10). `versionHistory` vem do mais novo para o mais antigo (usar o maior `updatedAt`). A URL aceita
  `{{contact.name}}`, `{{contact.email}}`, `{{contact.phone}}` (valores digitados) e muda a página de cima (iframe ok).
  Telefone com seletor de país (EUA por padrão; sem ele número sem código pode ir vazio): `fields[phone].enableCountryPicker: true`.
- Calendário: link `…/widget/booking/<id>?full_name=&email=&phone=` abre o formulário já preenchido (testado).
  Calendário sem `teamMembers` não tem horário nenhum ("No users found in the calendar"): `PUT services
  /calendars/{id} {teamMembers}` (o PUT mexe em `slotInterval` — mandar o valor antigo junto).
- Disponibilidade do calendário (v2) não fica no calendário (`openHours` vazio): `GET services /calendars/schedules/search
  ?locationId[&userId|&isCustom=true]` (`calendarIds`, `rules` por dia, `timezone`); editar com `PUT /calendars/schedules/{id}
  {rules, timezone}`; conferir com `GET /calendars/{id}/free-slots?startDate&endDate&timezone` (NorTex, 23/10).
- Merge fields em link de SMS: `{{contact.phone}}` sai "(480) 555-1234" (espaço quebra o link);
  usar `{{contact.phone_raw}}`. Filtros liquid (`| url_encode`) fazem o GHL não enviar o SMS.
- Link de review do Google: `writereview?placeid=<location.googlePlacesId>` da própria conta.
- IVR: gatilho `ivr_incoming_call` publicado liga o número ao workflow (`inboundCallService`). Com IVR,
  toda ligação de entrada vira "completed" → gatilhos de chamada perdida param; marcar `missed call`
  dentro do IVR (`scripts/pp_ivr.py`). Número externo em `ivr_connect_call.customNumbers`:
  `{country, phone (E.164), displayValue, isValid}`. Não ligar o IVR para um número que é do próprio
  IVR (loop): usar o número para onde a linha encaminhava.
- Horário no if/else: `conditionType: "date_time"`, `conditionSubType: "day_week"` (`"weekday"`/`"weekend"`) e
  `"quarter_hour"` (`"900"`, `"1700"` = HHMM, operadores `>=`/`<`), fuso da conta (Sunwave, `pp_poolheads_port.py`).
  IVR tocando usuários: `ivr_connect_call.users: [userId]` (toca os aparelhos do usuário; BluVantage).
- Templates (snippets): a leitura atrasa ~10-20 s depois do PUT (`pp_snippet_replace.py` espera).
- Texto próprio do cliente nas automações: `config/<cliente>_wording.json` + `scripts/pp_wording.py` (plan /
  `--test <inbox>` na Test Snapshot / `--apply`). Conta com esse config é pulada pelo `pp_mirror --apply`.
- Tirar contato de outros workflows: passo `remove_from_workflow` `{type: "remove_from_workflow", workflow_id: [ids]}`
  (testado). Mensagem recebida não dá para simular: `POST /conversations/messages/inbound` → 401 com o token Firebase.
- If/else por gatilho: `conditionType: "trigger"`, `conditionSubType: "trigger"`, `conditionOperator: "=="` (sem os
  dois o PUT dá 400 "missing its field/operator"), `conditionValue: <id do gatilho>` (Won Stage e
  Review Request ramificam assim pelas 3 etapas Won). Gatilho novo precisa de `workflowId`,
  `workflow_id`, `location_id`, `actions` no corpo — sem isso o PUT dá "Workflow not found".
- Usuário novo na sub-conta: `POST services /users/` `{companyId, firstName, lastName, email, type: "account", role,
  locationIds, permissions}` (sem `scopes`: 422; senha não obrigatória → primeiro acesso por "Forgot password" em
  app.poolprofits.com). Copiar `permissions` de um usuário existente com o mesmo papel. O `phone` vai na criação (o PUT depois recusa o token
  Firebase); `lastName` obrigatório. Apagar sub-conta: `DELETE services /locations/{id}?deleteTwilioAccount=true` (27/10).
- Labs (`/labs/features`) não aceita o token Firebase ("Auth channel not supported"): ligar no painel.
- Tag usada em passo/gatilho/if-else **tem que existir na conta** (`POST backend /workflow/{loc}/tags/create
  {tag}`): o passo funciona, mas o construtor mostra "Referenced Tag does not exist" (Frank viu no Won
  Stage). `scripts/pp_tags_missing.py` acha e cria as que faltam.
- Pular spam/cliente num workflow: if/else com `contact_detail` / `tags` / `index-of-false` (uma condição
  por tag) envolvendo a cadeia, em vez de filtro de gatilho (vale para qualquer gatilho; testado).
  Mid-chain: `parent` = branch que contém, `parentKey` = passo anterior (`scripts/pp_lead_alerts.py`).
- Pôr um contato num workflow publicado: `POST services /contacts/{id}/workflow/{wid}` com `{}`.
  O SMS de "internal notification" aparece na conversa do telefone do usuário (status delivered).
- Submissões de form: `GET services /forms/submissions?locationId&startAt&endAt` (`others` traz os
  campos e a página de origem). Aviso por e-mail do form: `formData.emailNotifications`. Mostrar a
  submissão na conversa: `formData.form.showSubmissionInConversationsFeed = true` (POST do form).
- Agendar envio: passo `wait` `{type: "time", startAfter: {type: "minutes", value: 1, when: "after"},
  window: {condition: "when", days: [<0 = domingo>], start: "09:00", end: "09:30"}, windowCondition:
  {field: "", operator: "", value: ""}}` segura o contato até a janela abrir (fuso da conta) e solta no
  início dela (testado). Campanha agendada = publicar + marcar agora (`pp_sms_campaign.py`).
  Drip depois da espera: passo `drip` `{batchSize, interval: {timeUnit: "minutes", value}}` solta em lotes
  a partir da abertura da janela. Editar o workflow publicado vale para quem já está parado na espera
  (testado; manter o id do passo de espera).
- Google Lead Form nativo: gatilho `google_lead_form_submitted` (`masterType: "internal"`), condição
  `{field: "adAccountId", operator: "==", value: <location.googleAdwordsId>, id: "adAccountId", type: "select"}`
  (+ opcional `formId` `is-any-of`; não há endpoint conhecido para listar os forms). Conta ligada pelo app novo "Google
  Lead Ads" fica com `googleAdwordsId` vazio: gatilho sem condição é aceito (LWR, 27/10). O lead só entra se o form
  estiver mapeado e **Active** em Settings → Integrations → Google Ads (botão Play/Map Fields); teste =
  Google Ads → campanha → Lead form → Edit → abrir o form → **Send Data** (help.gohighlevel.com 48001180147).
- Review gate (NPS) em qualquer conta, até de outra agência: `pd_lwr_nps_gate.py` (modelos `config/nps_form.json`,
  `config/nps_gate_steps.json`). Espera por condição com saída por tempo = passo `wait` com **`cat: "multi-path"` no
  nó** (não só nos atributos) + 2 nós `transition` (wait_condition / wait_timeout); sem isso o PUT dá 400
  "Transition parent … is not a multi-path action". Contato com nota: `PUT services /contacts/{id}
  {customFields: [{id, field_value}]}` dispara a espera.
- Ligação por IVR: a mensagem (type 24) tem `to` = nome da conta; o número discado está em
  `meta.ivr[<callSid>].to`. Gatilho `call_status` com `inbound_number` dispara mesmo com IVR (BluVantage).
  `meta.callStatusTriggerFired` lista os gatilhos que a ligação disparou (dá a linha quando há workflow por linha).
- Arquivo na biblioteca de mídia (ex.: MP3 de caixa postal): `POST services /medias/files/` `{name, contentType, parentId:
  "", altType: "location", altId, size}` → `{url (assinada), aknId}`; `PUT` do arquivo nessa URL com o Content-Type;
  `POST services /medias/files/verify {altId, altType, id: aknId}` → URL pública `assets.cdn.filesafe.space/…`
  (`/medias/upload-file` recusa o token Firebase). IVR tocando áudio: `sayPlayAttributes` com `widgetType: "play"` e
  `audioUrl` (Poolheads, 22/10).
- Funis/sites: `GET services /funnels/funnel/list?locationId` (passos com `pages[]`); print de qualquer página sem login
  pelo preview `https://app.gohighlevel.com/v2/preview/<pageId>` (Chromium headless `--screenshot`).
- Review Request de 13 contas (V9 carregado da conta de origem) lia a nota pelo id `ZIN3A1XVj7dvVTyCL3qX`, campo que a
  conta não tem: a espera nunca via a nota (todo mundo recebia o link do Google, a equipe nunca era avisada). Corrigido
  22/10 com `pp_review_fix.py` (id → NPS Score da conta; também link de review de outro lugar → place da conta).
  `pp_audit` agora acusa condição em campo inexistente.
- If/else por gatilho copiado de outro workflow guarda os ids dos gatilhos da origem → nenhum ramo bate (18 workflows,
  corrigido 23/10 com `pp_trigger_ref_fix.py`). O GET do workflow não traz os gatilhos: `Agency.triggers(loc, wid)`.
- If/else `contact_detail` com `has_value`: campo vazio cai no ramo else (testado 22/10). O "First Request?" do Review
  Request do V9 usa `has_value` no NPS Score → cliente sem nota sai do workflow sem pedido de nota/review (todas as contas).
- Onboarding de cliente: survey `efErcbOr4GAKXzZ28J4S` na sub-conta "Pool Profits" (`GET services
  /surveys/submissions?locationId`); cria a sub-conta em **America/Sao_Paulo** — corrigir o fuso
  (`PUT services /locations/{id} {timezone}`; `pp_timezone_fix.py`) e conferir custom values (`pp_onboarding_fill.py`).
- Tags de origem: `pp_source_audit.py` (contatos sem tag / leads sem origem, por linha) e `pp_source_tags.py`.
- E-mail interno de lead: `internal_notification` `{type: "email", email: {userType: "custom_email", to,
  subject, html}}`, um passo por endereço; merge de campo customizado (`{{contact.<fieldKey>}}`) sai
  preenchido (testado). Não fica registrado nas conversas — conferir na caixa (`pp_lead_email.py test`).

## Outra agência: Pool Duck

- Token Firebase próprio, **fora do repo** (arquivo de env carregado com `set -a; . <arquivo>`); o
  cache de token é por refresh token (`.token-cache-<hash>.json`), então as duas agências não se
  misturam. `GHL_DUMP_DIR=dump/poolduck` mantém os dumps fora do alcance dos scripts `pp_*`.
- Scripts `pd_*` (Lakewood Ranch); registro e pendências em `docs/poolduck-lakewood-ranch.md`,
  incluindo a API de funis (clone entre sub-contas, salvar página com `pageType: "live"`).

## Outra agência: BurchTech (GHL do Bill Burch)

- my.burchtech.app, company `syjenoyGz1jZ3ndDPkCm`; token em `burchtech.env` no scratchpad (fora do repo, já traz
  `GHL_DUMP_DIR=dump/burchtech`). Sub-contas: **Bluewater Brokerage** (`bw_forms.py`, `docs/bluewater-form-mapping.md`)
  e **The Pool Keepers** — conta viva do cliente (1.100+ contatos, fluxos próprios publicados): nunca `pp_mirror --full`
  nem `pp_e2e` ali; tudo que for nosso entra em draft e a publicação é combinada.
- Site da Bluewater (WordPress): nós ligamos o site ao GHL, não o web dev (Pedro, 20/10: somos o tech lead). Snippet
  `site/bluewater/bwb-ghl.php` via Code Snippets (`bw_site.py`, Application Password em `bluewater-wp.env` fora do repo);
  roda depois do que o site já faz (e-mail ao Bill, endpoint `bwb/v1` do Vik intocado).

