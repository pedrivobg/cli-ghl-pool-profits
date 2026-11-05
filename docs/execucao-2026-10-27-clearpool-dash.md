# 27/10 — Clear Pool Tucson: dashboards, pipeline e resultado (Pedro: "ele quer ver se nosso serviço traz resultado")

- Dashboards (API `services /reporting/dashboards?locationId`; detalhe `/reporting/dashboards/{id}`): eram 10, 9 vindos do
  snapshot em 30/04 (4 "Dashboard" iguais, 2 "Call Tracking", Appointment, Customer Communication). Apagados 7 com
  `DELETE /reporting/dashboards/{id}` corpo `{locationId, version: curVer-1}` (backup em
  `backup/clear-pool-solutions-tucson/dashboards-20261027.json`). Ficaram: "Dashboard" (padrão), "Call Tracking Dashboard",
  "Lead Attribution and Overview Dashboard Template". Renomear/editar pela API não deu (PUT → 409 "outdated version").
- Pipeline: tiradas as etapas vazias e sem uso "Current Customer" e "Drip Campaign | Reactivate" (backup). Ficam 8.
- Resultado (contatos com tag `new lead`/`won`, spam/DND à parte), abr–out: 166 leads reais, 37 viraram cliente (22%);
  Google Ads 44 → 8, Website & GBP 112 → 26, outros 10 → 3; 100 spam filtrados. Página: Artifact "Clear Pool Tucson Lead
  Results" (https://claude.ai/artifact/Rv8ANR4PAYzp6n7NuEJYaJ), dados fixos de 27/10.
- **Status e valor** (Derek: só fica open o que dá para contatar; média $150 em todos). `scripts/cp_opps_fix.py`:
  "Lost Lead" começa com status lost, "DND Contact" (SPAM) com abandoned, novo "Out of Scope - Close" (abandoned); os
  "Create Or Update Opportunity" de entrada com $150 (Google Ads tinha 180) e status open (quem volta a ligar reabre como
  New Lead). Testado com um card movido pelas 3 etapas. 230 cards acertados só com status + valor (sem mudar etapa,
  nenhum workflow disparou; só o registro "Opportunity status changed"): open 3 (New Lead 1, In Communications 2), won 37,
  lost 73, abandoned 118, todos $150.
- **Valores por resultado + abandoned apagado** (Derek). `scripts/cp_values_fix.py`: card novo $2.160 em todos os fluxos de
  entrada; "Won Customer" + "Create Or Update Opportunity" won $2.160; "Repair Customer Won" won $150; "Lost Lead" lost $0
  (card fica); "DND Contact" (SPAM) e "Out of Scope - Close" → "Remove Opportunity" (apaga o card; contato fica com as
  tags). O passo "Update opportunity" não grava valor (4 variantes testadas). Teste com um card passando por Won → One Time
  → Lost → SPAM: certo em cada etapa, apagado no fim. Cards: 92 valores acertados, 118 de spam/fora da área apagados
  (backup `opportunities-before-values-*.json`). Agora: 3 open $2.160, 16 won $2.160, 21 won $150, 73 lost $0 → GHL mostra
  37/115 = 32%. PDF (`cp_results_report.py`) atualizado: $37.710 em valor de clientes.
- **Aviso de chamada perdida para o Derek** ("quando não atender e deixar voicemail"). O recado é anexo de áudio da
  mensagem da ligação; nenhum gatilho/condição vê isso → aviso em toda chamada perdida (`scripts/cp_missed_notify.py`):
  SMS para o Derek + e-mail para tucson@clearpoolsolutions.com com nome, telefone, linha e "ouça o recado em
  Conversations". Também para cliente atual (ramo novo "Current customer": perdeu → aviso marcado CURRENT CUSTOMER, sem
  card nem SMS ao cliente); spam/DND → nada. Testado numa cópia (4 casos).
- **Derek dono de tudo** (`scripts/cp_owner.py`). O card criado por workflow herda o dono do contato (testado; o passo de
  card não tem campo de dono). Novo "Contact Created -> Assign Derek" + "Assign to Derek" como 1º passo dos 7 fluxos de
  entrada que criam card (gatilhos reapontados). Existentes: 416 contatos e 94 cards atribuídos (backup dos donos antigos);
  agora 453/453 e 114/114. Teste: contato novo ganhou o Derek como dono sozinho.
- **Avisos internos de lead novo (verificação)**. SMS internos para o Derek entregues (último 16/10, Google Ads form). Achado:
  os leads do site chegam com a tag `website from fill` (erro de digitação da integração do site; 33 contatos, fonte
  "Website Form Fill") e o "Website Form Fill To Pipeline" só disparava com `website form fill` → nenhum aviso/tarefa para
  lead do site. Gatilho novo com `website from fill` (o antigo fica) + e-mail para tucson@ depois do SMS; e-mail também no
  "AdWords Form - New Lead". Leads do site sem aviso na última semana: Johnathan Mougin (23/10, sem card), Kelly Polder
  (24/10), Alisha Simon (26/10). SMS de lead novo (linhas Google Ads e Website) não têm aviso interno (cada texto dispara
  o fluxo; o app do GHL já avisa) — não mexido.

## 28/10 — depois da call (Derek, Ed, Frank)

- **Review Request** (draft, `scripts/cp_review_request.py`): o fluxo do snapshot já existia em draft com o NPS Score da
  própria conta e o link do Google certo. Só o tempo mudou: Won semanal 14 → 30 dias, One Time Repair 1 → 2 dias; + espera
  de 182 dias → SMS de review de novo (uma vez; o GHL não sabe quem já deixou review). Custom value "Google Review Link"
  (vazio) → place da conta. Continua draft (publicar é decisão do Derek).
- **Ligações perdidas 29/09–27/10** (mensagens type 24: `meta.ivr[sid].status` `no-answer` = tocou e o Derek não atendeu;
  sem status = desligou no IVR): 13 + 14. Por contato: spam/DND 9, cliente 1, atendidos depois 2, o próprio Derek
  testando 1 (2/10, "D Carbonneau"), Frank 1 (27/10, teste), **lead real sem retorno: P Carlson (520) 342-4654** (18/10).
  Sem SMS em massa: vai o nome para o Derek ligar.

## 29/10 — NorTex: landing pages do Atif (DNS, form → calendário, aviso de agendamento)

- `go.nortexpools.com` está cadastrado no GHL desde 31/07, mas o DNS (Cloudflare, aspen/brady) **não tem registro**
  (NXDOMAIN) → as URLs dão erro. As outras contas usam CNAME → `sites.ludicrous.cloud`. Falta criar no Cloudflare (sem acesso).
- Form do site ("New Website Form") redireciona para o calendário "Pool Service Appointment" (`hgie4SC4ARRYtGFTC8Aw`)
  com `full_name/email/phone`; os 2 forms das LPs (WEEKLY/REPAIR) agora fazem o mesmo (`scripts/nx_ads_booking.py`,
  backup dos forms). As páginas de obrigado do Atif deixam de ser usadas (o calendário mostra a mensagem dele).
- Nenhum agendamento avisava ninguém (notificações do calendário apagadas; Appointment Confirmation em draft). Novo
  "Appointment Booked -> Notify Fareed" (status confirmed; o calendário auto-confirma): SMS + e-mail ao Fareed.
  Testado o e-mail numa cópia; o gatilho de agendamento real fica para o teste com o DNS no ar.

## 30/10 — NorTex: forms das landing pages com o visual do site (cliente via Val)

- `scripts/nx_ads_form_style.py`: WEEKLY e REPAIR refeitos a partir do "New Website Form" (caixa azul-marinho, borda
  dourada, Full Name / Phone / Email, botão dourado); cada um mantém o redirecionamento ao calendário, o texto do botão,
  o consentimento (A2P) e os links Terms/Privacy em branco; REPAIR mantém o equipamento e a nota dos $150. Endereço/
  cidade/CEP saíram, como no site. Prévia em forms temporários (apagados) + print das páginas no ar; backup dos forms.
- Teste real anterior (30/10, form + agendamento) continua valendo para fluxo/avisos; o aviso do Fareed agora mostra
  o endereço vazio (o form não pede mais).

## 30/10 — YardSpring: correções do teste da Val nos 3 forms das landing pages

- `scripts/ys_form_fix.py` (backup dos forms): redirecionamento ia para yardspringpools.com/thank-you-… (WordPress, 404)
  → páginas de obrigado do Atif no mesmo funil do GHL (go.yardspringpools.com/weekly-pool-service-3356 / -8572 / -6305);
  First + Last → Full Name; Street/City/ZIP → "Property Address" com busca do Google (`group_address`; o form guarda
  `address.autoCompleteEnabled` e preenche cidade e CEP — o CEP continua alimentando o "service area zip" do fluxo).
  Conferido na página no ar (campos novos); a busca do Google não abre daqui (rede da sessão).

## 02/11 — Bonneville Pool Maintenance (conta nova, `DeSfqW31OleIiU7eUt35`, Kaysville UT; survey do Justin Jeppsen)

- `pp_onboarding_fill --timezone` (survey de 02/11, anterior de 29/10): fuso Sao_Paulo → America/Denver; Green to Clean
  "null" → vazio. Correções básicas (backup): `a2p_verification_number` provisório (801) 915-8582 (sem número na conta —
  "No Twilio account"), Client Domain Name sem https, Service Area "Kaysville", missed-call nativo desligado.
- `pp_mirror --apply` (11 workflows do modelo publicados), `pp_forms` (nada), `pp_nps` (NPS Form + link), `pp_fix
  --drop-booking --include-drafts`, `pp_tags_missing`, `pp_skip_tag` (já tinha), `pp_review_fix` (nada).
- **Erro do `pp_fix`**: leu o dump de antes do `pp_nps` (link do NPS vazio) e trocou o link do SMS do NPS por "Just reply…",
  deixando `?email=…&phone=…` solto. Restaurado do backup (igual ao modelo). Lição: re-dump depois do `pp_nps`.
- Veio do snapshot ainda sem o Refresh: Sequential Call Routing genérico (sem usuários/caixa postal da BluVantage, gatilho
  com 6 números dela removido) e o gatilho do AdWords Call In no número de Tucson removido (os dois em draft). Os 4 funis
  "Simple Pool Care"/"LP Teste" continuam na conta (não mexido).
- Resultado: auditoria 0 ALTA, `pp_ready` 0 ERRO (com `--place` do link g.page do survey; Google não conectado).
- Falta: número de telefone + A2P (sem número nenhum SMS sai, nem os avisos internos por SMS); o site não tem privacy/
  terms (404) → A2P pelo "New A2P Verification" num subdomínio; conectar Google Business; primeiro acesso do Justin.

## 03/11 — Pool Palooza: Google Ads Lead Form "Google Ads - Lead Form" (Val)

- Conta com setup próprio (Pool Service Accelerator): o "⚙️ Pool Service Lead Engine" (publicado) já recebe Facebook
  lead form, TikTok, forms do site, Angi e Yelp e trata todos igual (aviso interno, dono, card em "1. Leads" → New Lead,
  sequências de SMS/e-mail, pesquisa). Ganhou o gatilho **Google Lead Form Submitted** (sem filtro de conta: Google Ads
  não conectado pela conta — `googleAdwordsId` vazio — como na LWR/YardSpring). Passos intocados (33), backup em
  `backup/pool-palooza/`.
- Novo "Google Lead Form - Tag" (mesma pasta, publicado): mesmo gatilho → tags `google ads` + `google ads lead form`
  (origem, no padrão do "TAG Orchestrator" deles).
- Falta (Val): no GHL da Pool Palooza → Settings → Integrations → Google Lead Ads: mapear os campos do form "Google Ads -
  Lead Form" e deixar **Active**; depois Send Data no Google Ads (me avisa antes: o lead de teste entra nas sequências e
  avisa a equipe; eu apago).

## 03/11 — NorTex (Val/Fareed): endereço no form, Lead Form e SMS do Google Ads

- Fareed: "o endereço não apareceu depois de escolher data/hora". O widget de agendamento (calendário "Pool Service
  Appointment", form "Appointment Booking Form") só pede nome/e-mail/telefone (já preenchidos) e o form do site também
  não pede endereço. Os 2 forms das LPs (agora em promo.nortexpools.com) ganharam **Property Address** obrigatório com busca
  do Google (preenche rua/cidade/estado/CEP), antes do calendário (`nx_ads_form_style.py`, prévia + backup).
- `scripts/nx_ads_line.py` (cópia do `ys_ads_line.py` com os ids da NorTex; ligações já cobertas pelo IVR): "Google Ads
  SMS - New Lead" (SMS na linha (469) 218-3416) e "Google Lead Form - New Lead" (Google Lead Form Submitted; o form cobre
  Weekly + Repairs; serviço no campo "Service" se o form perguntar), tags `new lead`/`adwords`/`google ads - sms|lead form`
  (+ `new form fill`), card em New Lead, SMS + e-mail + tarefa ao Fareed. Testado em cópias (6 casos), publicado.
- Falta: Google Ads conectado no GHL da NorTex (`googleAdwordsId` vazio) e o form mapeado/Active no app Google Lead Ads;
  Send Data; envio real do form das LPs com endereço + agendamento.

## 04/11 — Poolheads: migração da conta antiga (outra agência) — etapa 1: templates

- Token da conta antiga ("Poolheads Pool Service & Repair", `PvPul1DiA2pXShC0xfDD`) em `poolheads-old.env` no scratchpad
  (fora do repo; dump em `dump/poolheads-old/`). Só leitura na conta antiga.
- Inventário: 20 workflows (8 publicados), 9 templates de SMS, 5 de e-mail (1 + pasta "Email Confirmation Templates" com 4),
  5 calendários, 5 forms, 1 pipeline, 16 campos, 4 usuários (Felipe, Jorge Arias, Jose Cobo, "Main Office Phone").
- `scripts/ph_migrate_old.py emails|snippets --apply`: os 5 e-mails na conta nova com os mesmos nomes e pasta (como HTML: o
  JSON do editor arrasta-e-solta não é baixável; o HTML é o e-mail renderizado, editável no editor de código); as 5
  imagens que moravam no storage da conta antiga foram copiadas para a biblioteca de mídia da nova e os links trocados (0
  links antigos restantes; comparação visual idêntica). Os 9 SMS com nome e texto iguais.
- Próximo: campos, calendários (inativos), forms, workflows em draft (pasta "Old account", ids trocados), comparação.
- **Etapa 2 (04/11)**: 16 campos; 5 calendários **inativos** (mesmas configurações e horário seg–sex 8–17, Felipe como
  membro; e-mail de confirmação ao cliente apontando para os templates migrados — conferido igual ao original); 5 forms
  (Mainsite, 2026 - Pool Service - V69, Repairs LP V16, [Service]/[Repairs] Google LP Form V4); 11 workflows em draft
  "[Old account] …" com todos os ids trocados (usuários → Felipe, pipeline/etapas por significado, calendários, campos e
  chaves de merge, templates, forms) e gatilhos copiados (inativos): 0 ids antigos restantes. Não copiados: "After Hours
  Message" e "Business Hours Call Routing" (portados e no ar desde outubro) e 7 vazios. Tag `current customer` criada.
- **Antes de cancelar a conta antiga**: o "LVB - Meta Service" (publicado lá) recebe leads por webhook de um serviço
  externo → trocar a URL no serviço para a nova (`…/hooks/PeUynYCMm8e6PJMy785O/webhook-trigger/zxySSbrHhRqaWat6wF0i`) e
  publicar o draft; os forms antigos que estiverem em páginas da conta antiga continuam caindo lá até as páginas mudarem.
- Histórico de conversas: a API não deixa gravar mensagens no Conversations com o nosso acesso (o mesmo limite do
  `/conversations/messages/inbound`); dá para pôr o histórico de 6 meses como nota em cada contato (~500 conversas).

## 03/11 — NorTex: conversões offline do Google Ads (Val)

- Val conectou o Google Ads da NorTex (`googleAdwordsId` 3853304460) e criou 2 conversões offline (UPLOAD). O GHL as
  lista em `GET services /ad-publishing/google/conversions?locationId`: "Appointment Booked" 7887965192, "LP Form Submit"
  7888097011.
- `scripts/nx_ads_conversions.py apply` (backup de cada workflow): "LP Form Submit" no passo "Google Ads conversion" (estava
  vazio) de "Google Ads LP - Weekly" e "- Repair" (ramo de lead novo, depois do card); "Appointment Booked" como último
  passo de "Appointment Booked -> Notify Fareed" (gatilho continua no 1º passo). Os 3 publicados, re-entry mantido,
  gatilhos ativos. gclid = `{{contact.attributionSource.gclid}}` (a página do LP grava o gclid da URL no contato).
- Teste: cópia temporária com gclid falso rodou sem erro de configuração; o log de execução não tem endpoint conhecido
  (4 caminhos 404). O teste de ponta a ponta precisa de um clique real no anúncio (gclid válido) — passo a passo no TODO.
- "Send Data" do lead form: nenhum contato novo de teste na NorTex nem na Pool Palooza (últimos contatos: 02/11).
- "Google Ads SMS - New Lead" também tem um passo de conversão vazio: Val criou só as 2; fica vazio até ela dizer.

## 03/11 — BluVantage: "people say we called them" (Paul/Vanessa via Frank)

- 404-334-2495 = número principal da conta (Twilio no GHL desde 28/05, linha "Printed Marketing Materials", no IVR).
- Os 2 casos da Vanessa: Gerald Kearse (+14045205268, 30/10 15:05Z) e Sonia (+14047215757, 02/11 19:55Z). Os dois
  contatos nasceram na própria ligação de entrada; nenhuma ligação ou SMS de saída do GHL para eles antes, de nenhum
  número. Transcrição da Sonia: "I missed a call from this number. I'm just calling back" — a equipe não achou histórico.
- Nenhum workflow publicado liga para fora (só o IVR `ivr_connect_call` / voicemail). Ligações de saída do GHL usam
  local-presence dialing (rodam entre as 7 linhas; 14 das ~80 recentes saíram pelo 404-334-2495), mas todas ficam
  registradas na conversa — e não há nenhuma para esses contatos. Outras transcrições de outubro: nenhum caso parecido.
- Conclusão: a ligação não saiu do GHL. Mais provável: spoofing (spam/robocall usando o número deles como caller ID) ou
  alguém ligando por outro app/aparelho que mostra esse número. Sem acesso ao registro do Twilio fora do GHL.
- Efeito colateral: esses retornos viram contato com tag `new lead` + `printed marketing materials` (conta como lead).

## 03/11 — Pool Shack: 2 números de rastreamento (Frank comprou; Rob aprovou)

- Rob: só usa a nossa agência (a Pool Monopoly o colocou num GHL, sem uso). Números: Weekly Pool Maintenance +14804181231,
  Repairs / Installs +14805683370 — sem encaminhamento (o da conta, 480-428-0655, encaminha para o Google Voice
  480-798-2888). Não há endpoint conhecido para `forwardingNumber`: Pedro configura na tela.
- `scripts/ps_ads_lines.py`: "Google Ads Call - Weekly" e "- Repairs" (pasta dos Google Ads LP), Call Status inbound na
  linha → spam/DND nada; 24 h nada; cliente → tags + aviso EXISTING CUSTOMER; novo → tags `google ads`, `weekly|repairs`,
  `google ads - call`, `new lead`, `adwords`, card "Google Ads Call - Weekly|Repairs", conversão (vazia), SMS + e-mail +
  tarefa ao Rob. Teste em cópias: 6/6 ✓, limpo.
- Correção básica (backup): "AdWords Call In - New Lead" (gatilho no número da Clear Pool, texto da Clear Pool) e
  "Sequential Call Routing" (números e usuários da BluVantage) estavam publicados → draft.
- WordPress: thepoolshack.kinsta.cloud é o mesmo site (redireciona para thepoolshackarizona.com), WPForms 440/443,
  Application Passwords disponível.

## 03/11 — NorTex: Meta Conversions API (Val) — Weekly = Meta Ads, Repair = Google Ads

- `scripts/nx_meta_capi.py` (token lido do draft da Val "Forms/Meta Conversion API", nunca impresso; dataset 2163998117807974;
  a Meta responde ao token "Missing Permission" na leitura = token válido só para enviar eventos).
- "Google Ads LP - Weekly" → **"Meta Ads LP - Weekly"**: tags `meta ads - weekly` + `meta ads` (+ `meta ads lp weekly 24h`)
  no lugar de `google ads - weekly` + `adwords`; Landing Page, origem do card e avisos dizem Meta Ads; o passo de conversão
  do Google virou o evento Meta **Lead** (`facebook_conversion_api`, `event_type: funnel_event`, `event_name: Lead`,
  fbclid `{{contact.lastAttributionSource.fbclid}}`) no ramo de lead novo. Form renomeado "META ADS – WEEKLY" (redirect ok).
- "Appointment Booked -> Notify Fareed": depois do Google "Appointment Booked", if/else tag `meta ads - weekly` → evento
  Meta **Schedule** (fbclid da primeira visita: o widget de agendamento chega sem fbclid). Gatilhos e re-entry intactos.
- "Google Ads LP - Repair" igual (Google, "LP Form Submit"). O draft da Val ficou como está.
- Formato do passo Meta visto em Orange Tree / Pool Duck WC. Na Wesley Chapel (Pool Duck), 2 workflows têm o token colado
  no campo `pixel_id` (o evento não sai) — avisar.
- Send Data: ainda nenhum lead de teste na NorTex nem na Pool Palooza (03/11 15:40 UTC).

## 03/11 — Pool Shack: forms do site (WPForms) → GHL

- Antes: o site (thepoolshackarizona.com, WordPress + WPForms) já perguntava o "Service Needed", mas nenhum envio chegava
  no GHL. Forms: **440 "Request a Quote"** (home: Name, Phone, Are You a New Customer?, Service Needed) e **443 "Main
  Contact / Service Form"** (home e /contact/: Full Name, Phone, Email, Address, Postal Code, Service Needed, Message,
  consentimento). reCAPTCHA v3 do WPForms nos dois.
- O que já existia no GHL: "Website Form Fill To Pipeline" (card Pool Leads → New Lead, origem "Website Form", tags
  `new lead` + `form fill`, SMS ao Rob, tarefa) dispara **só por envio de form do GHL** (3 forms); nada na conta escuta
  a tag `website form fill` (não existia) nem `new lead`. "Atribuition" (contato criado → dono Rob) roda para todo contato.
- GHL (`scripts/ps_site.py ghl-live`, pasta do Website Form Fill): **"Website Form - Request a Quote"** e **"Website Form -
  Main Contact / Service Form"**, publicados, gatilho inbound webhook (URLs em `backup/the-pool-shack/webhook-urls.json`):
  criar/atualizar contato (nome, sobrenome, telefone; no 443 também e-mail, endereço, CEP) → campos que já existiam
  (Service Needed; Are You A New Customer no 440; Message no 443) → tags `website form fill` + `new lead` → passo **"Add to
  workflow" → "Website Form Fill To Pipeline"** (o card e o aviso ao Rob são os de sempre, uma vez só; nenhum campo criado).
  Formato do passo (visto na Wesley Chapel / Bluewater): `{type: "add_to_workflow", attributes: {input_trigger_params:
  false, type: "add_to_workflow", workflow_id}}` — testado: o contato entra no workflow alvo.
- Site (`ps_site.py apply`): Code Snippets instalado (não havia) + snippet #5 "The Pool Shack forms → GHL (Pool Profits)"
  (`site/poolshack/ps-ghl.php`), hook `wpforms_process_complete` (prioridade 99, depois dos e-mails/confirmação do
  WPForms; só envio aceito pelo WPForms). Nome dividido no 1º espaço, telefone US → +1XXXXXXXXXX, página de origem
  (`page_url`). Envia se tiver telefone ou e-mail (o 440 não tem e-mail). Rotas nossas com `?key=`
  (`backup/the-pool-shack/site-key.txt`): `/ps-ghl/v1/status` (últimos 30 envios) e `/ps-ghl/v1/test` (o `send` só vai
  para um webhook de teste; webhook do ar → 400). Nada mais mexido (plugins, tema, páginas, forms do WPForms).
- Testes: PHP local (`site/poolshack/test-ps-ghl.php`, 12/12); `ghl-test` (cópias ZZ TEST cujo "Add to workflow" vai
  para um alvo que só põe tag, POST direto) 2/2 ✓; `apply` (home ok com os 2 forms, mapeamento no site 2/2 ✓);
  `ghl-test --via-site` (o snippet no servidor posta nas cópias ZZ TEST) 2/2 ✓ — contato, campos, tags, alvo, sem card.
  Contatos, workflows e tags de teste apagados. Os contatos de teste passaram pelo "Atribuition" (dono Rob), como nos
  testes anteriores da conta.
- Falta: envio real pelo site (Pedro, avisando o Rob antes — o aviso vai para ele): passo a passo no TODO, item 5.

## 03/11 — Pool Shack: teste real das linhas (Pedro, 17:04–17:05 UTC)

- Encaminhamento dos 3 números → Google Voice (480) 798-2888 ✓ (Pedro configurou).
- Weekly (480) 418-1231, sem atender ("no-answer"): "Google Ads Call - Weekly" + "Missed Incoming Call To Pipeline" ✓;
  SMS "Sorry we missed your call" ao lead ✓, card, SMS + e-mail ao Rob ✓.
- Repairs (480) 568-3370 (6 s, "completed"): "Google Ads Call - Repairs" + "Answered Incoming Call To Pipeline" ✓, aviso ao
  Rob ✓.
- Linha principal (480) 428-0655 caindo na caixa postal do Google Voice: status "voicemail" → "Missed Incoming Call To
  Pipeline" + "Website & GBP Call - Tag" ✓. Ou seja: o recado do Google Voice conta como chamada perdida e o SMS sai
  para quem liga pela primeira vez (aqui não saiu de novo porque o mesmo contato já tinha recebido 1 min antes —
  re-entry desligado, como deve ser). Pedido do Rob respondido.
- Contato de teste (+55 37 …), card e 2 tarefas apagados (backup). Pendente: envio real dos 2 forms do site.
- 17:53 UTC — envio real dos 2 forms do site (Pedro): snippet → GHL HTTP 200 nos dois (`ps_site.py status`); contato
  com nome, e-mail, telefone, endereço/CEP, Service Needed, Are You A New Customer, tags `website form fill` + `new lead`;
  card em New Lead (fonte Website Form), 2 SMS "NEW LEAD - Website Form" ao Rob (1 por form, delivered) e 2 tarefas.
  Contato de teste (era o "ZZ Teste Pedro" de 23/10), card e tarefas apagados (backup). Pool Shack: tudo testado.

## 03/11 — NorTex: teste real do Meta (Pedro, 18:00 UTC) + funil renomeado

- Funil "Google Ads - Premium Weekly Pool Cleaning" → **"Meta Ads - Premium Weekly Pool Cleaning"** (`dYgPQmS6io7iTWitYQbE`,
  só o nome; domínio, caminhos e código do head iguais; página 200). As páginas estão em **promo.nortexpools.com** (o "go"
  dá 404). Nenhum workflow ainda usa tag Google para o Weekly.
- promo.nortexpools.com/premium-weekly-pool-cleaning?fbclid=TEST-POOLPROFITS → form + agendamento: tags `meta ads - weekly`,
  `meta ads`, `new lead`; Landing Page "Meta Ads LP - …"; card "Meta Ads LP - Weekly" em New Lead; confirmação SMS + e-mail
  ao lead; aviso "NEW META ADS LEAD" (SMS + e-mail) e "NEW APPOINTMENT BOOKED" ao Fareed; agendamento confirmado.
- O redirecionamento leva o fbclid para o widget de agendamento: `lastAttributionSource.fbclid` = TEST-POOLPROFITS na
  hora do agendamento (a primeira visita do contato antigo não tinha). O evento Schedule passou a usar
  `lastAttributionSource.fbclid` (backup; script atualizado). Conferência dos eventos no Events Manager: Val.
- Contato de teste, agendamento (05/11 8h no calendário do Fareed), card e tarefas apagados (backup).
- 18:04 UTC — teste do Repair (Google) pelo Pedro: tags `google ads - repair`, `adwords`, `new lead`; Service, Equipment e
  Landing Page; card "Google Ads LP - Repair"; confirmações ao lead; avisos de lead e de agendamento ao Fareed ✓. Sem
  evento Meta (não tem a tag do Weekly) ✓. **gclid vazio**: a página foi aberta direto (Direct traffic), não por um clique
  no anúncio (anúncio segmentado para Frisco/TX não aparece do Brasil) → as conversões do Google foram enviadas sem gclid
  e o Google não conta. Conferência do lado do Google fica com a Val (primeiro lead real de anúncio / diagnóstico das
  conversões). Contato, card e agendamento apagados (backup).

## 03/11 — NorTex: linha do Meta Ads (469) 535-7838 (Val)

- Val comprou +1 469-535-7838 ("Facebook") só para a página Weekly (Meta Ads); o Atif põe o número só nela.
- Como a NorTex toca hoje: nenhuma linha tem encaminhamento; as duas ((469) 238-2660 principal e (469) 218-3416 Google
  Ads) passam pelo IVR "IVR SPAM Detection" ("press 1" → toca o usuário do Fareed; sem atender → recado + tag
  `missed call` → "Missed New Lead - Initial SMS Follow-up"; sem tecla → nada no IVR, o "Answered Incoming Call To
  Pipeline" trata como chamada perdida). A linha nova estava sem IVR (ligação não tocava ninguém).
- `scripts/nx_meta_line.py apply`: o número entrou no gatilho do IVR (backup `backup/nortex-pools/trigger-TUyctF6wtZskP1Bc8IRv-*.json`;
  só a lista de números mudou) → `inboundCallService` = IVR, toca igual às outras. Nenhum encaminhamento necessário.
  "Answered / Missed Incoming Call To Pipeline" não filtram número: continuam valendo para a linha (tags `new lead` /
  `inbound call` [/ `missed call`], card "Inbound Call", tarefa). Linha principal não tem workflow de tag; a do Google tem
  "Google Ads Call - Tag" — a do Meta ganha as tags no próprio fluxo (`meta ads - call` / `meta ads - sms`).
- Publicados na pasta do "Meta Ads LP - Weekly": **"Meta Ads Call - Weekly"** (`33f7adc7…`, Call Status inbound, In Phone
  Number = a linha) e **"Meta Ads SMS - Weekly"** (`168883e9…`, Customer Replied SMS, In phone number = a linha); gatilhos
  ativos e só nesse número. Rota: spam/DND → nada; últimas 24 h → nada; cliente atual → tags + Service + SMS/e-mail ao
  Fareed "(EXISTING CUSTOMER)", sem card; lead novo → tags `meta ads - weekly`, `meta ads`, `meta ads - call|sms`, `new
  lead`, 24 h; Service "Weekly Pool Cleaning" (como o LP Weekly); dono Fareed se vazio; SMS + e-mail + tarefa ao Fareed
  ("NEW META ADS CALL|TEXT - PREMIUM WEEKLY POOL CLEANING"); card em New Lead (origem "Meta Ads Call|SMS - Weekly").
  Sem conversão do Google. Ligação: o card vem 1 min depois e o workflow não permite 2º card → atualiza o card "Inbound
  Call" que o fluxo genérico abre na mesma ligação (1 card só, origem Meta). Todo ramo: espera 1 dia → tira a tag 24 h.
- Teste (`test --to pedro@poolprofits.com`, cópias ZZ TEST, sem SMS ao Fareed): 7/7 ✓ — ligação novo (+ 2ª entrada
  barrada), novo com card "Inbound Call" já aberto (vira 1 card "Meta Ads Call - Weekly"), cliente, spam; SMS novo (+
  repetição), cliente, spam. 5 e-mails [TEST] chegaram, nenhum do spam/repetição. Contatos, cards, tarefas e workflows
  de teste apagados (conferido).
- Falta: ligação + SMS reais (Pedro; passo a passo no TODO, item 10).
- 19:07 UTC — teste real da linha Meta (469) 535-7838 (Pedro): ligação passou pelo IVR com o número certo e disparou
  "Meta Ads Call - Weekly" + "Answered Incoming Call To Pipeline"; tags `meta ads - weekly`, `meta ads`, `meta ads - call`,
  `missed call`, `new lead`; Service = Weekly Pool Cleaning; dono Fareed; SMS + e-mail + tarefa ao Fareed (ligação) ✓.
  SMS "TEST" → "Meta Ads SMS - Weekly": tag `meta ads - sms`, aviso + tarefa ao Fareed ✓. SMS de chamada perdida ao lead
  saiu do **número principal** +14692382660 (não do Meta). Card: 1 só, mas a origem ficou "Inbound Call" (o passo do
  Meta atualiza o card do fluxo genérico, não troca a origem) e o SMS de resposta levou o card para In Communication
  (fluxo da conta). Contato, card e tarefas apagados (backup).

## 03/11 — NorTex linha Meta: correção da origem do card + número de saída do SMS

- Causa do "Inbound Call": o card do fluxo geral nasce antes; o "Create/Update Opportunity" **troca a origem** ao
  atualizar (testado), mas no teste real o card já estava em In Communication (o SMS de resposta moveu) e o passo do
  Meta, com etapa New Lead, não volta etapa → não atualizou nada.
- Correção (backup de tudo): "Meta Ads Call - Weekly" cria o card **primeiro** (logo depois das tags, sem espera; gatilho
  reapontado para o 1º passo). "Answered Incoming Call To Pipeline" (2 ramos) e "Missed Incoming Call To Pipeline":
  antes do card, espera 1 min + if/else "Meta line call?" (tag `meta ads call 24h`) → ligação da linha Meta não ganha
  card "Inbound Call" (nem a tarefa de 1 h do fluxo geral: o Meta já cria a dele); outras ligações seguem iguais, com o
  card 1 min depois. Teste em cópias: contato da linha Meta → 1 card "Meta Ads Call - Weekly" em New Lead; outra
  ligação → "Inbound Call" em New Lead. Limpo.
- Número de saída do SMS de chamada perdida: o passo `sms` de workflow ignora qualquer campo de origem (testei
  `fromNumber`, `from_number`, `from`, `phone_number`, `phoneNumber`, `fromPhone`, `fromNumberId`… — gravados, mas o SMS
  sai sempre do número padrão +14692382660). 3 SMS de teste no celular do Pedro, contatos apagados. Sem solução por API.

## 03/11 — Stay Fresh: call com o Frank (walkthrough) + avisos para o Kris

- Walkthrough das automações com o Frank (resumo mandado por DM no ClickUp). Pedido: o Kris ("Chris", usuário Kris
  Fitzhugh, Kris@stayfreshpools.com, +14807721420) recebe os avisos de lead novo por e-mail e SMS.
- "Website Form Fill To Pipeline" (backup): "New Lead SMS" agora vai para Mike **e Kris**; passo novo "New Lead Email -
  Kris" (e-mail com nome, telefone, e-mail, cidade, origem). E-mail testado numa cópia (chegou no pedro@), cópia apagada.
- Em aberto (perguntado ao Frank): avisos de ligação para o Kris (hoje ligação só gera tarefa para o dono, Mike);
  re-entry em Quote Sent/No Response/Won/Lost; IVR (o Frank traz como o cliente quer).

## 04/11 — NorTex: tag da linha Website & GBP (Val)

- `pp_line_tag.py --only NorTex --apply` → "Website & GBP Call - Tag" (ligação de entrada em +14692382660 → `website & gbp`)
  + novo "Website & GBP SMS - Tag" (SMS recebido no mesmo número). Os dois com if/else "Came from an ad line?": contato
  com `meta ads`/`adwords`/`google ads - …` não ganha a tag (o SMS de chamada perdida de todas as linhas sai do número
  principal, então resposta de lead de anúncio cai nele). Teste: contato comum → `website & gbp`; contato `meta ads` →
  sem a tag. Limpo. Val respondida no DM.

## 04/11 — Pool Duck LWR: hero novo da landing page comercial (Val/Atif, inbox watch)

- Cliente pediu hero com piscina de hotel/condomínio. O Atif trocou no preview (sub-conta "Pool Duck" da Pool Profits);
  a Val viu as duas versões diferentes e o Atif passou para mim. Diferença real entre as páginas: só o CSS do cabeçalho
  (`trackingCode.headerCode`: imagem Unsplash nova, desktop + mobile).
- `pd_lwr_commercial_page.py export` + novo modo **`css`** (token Pool Duck): copia só o CSS das páginas do Atif para as
  páginas no ar da LWR, mantendo o corpo (telefone do Google Ads 941-541-5942, form, tag). Backup
  `backup/pool-duck-lakewood-ranch/page-yzmSuNMFMbGEBIaZNJlZ-20261104-191912.json`; obrigado sem mudança.
- Teste: HTML ao vivo com a imagem nova na 1ª leitura; prints desktop/mobile iguais ao preview do Atif. Respondido na
  thread (86bcf4mbr); tarefa 86bcycgby fechada. NorTex (5 itens): só agradecimentos / já respondidos.
- 20h UTC (inbox watch, 1 item): a Val respondeu ao Atif na thread ("for now the same number is fine"), ou seja, fica o
  número de rastreio do Google Ads (941-541-5942), que já está na página. Ninguém me pediu nada: não respondi e não mexi
  em nada. O ledger não tem ferramenta de update pelo MCP do n8n → linha nova com o mesmo `item_id` e status `done`.

## 04/11 — Stay Fresh: respostas de campanha SMS viram New Lead + avisos para o Kris (Val, inbox watch)

- Val (DM em grupo no ClickUp): antes de qualquer campanha SMS, revisar painel/automações com a Stay Fresh como
  referência + checklist de lançamento (aprovação do cliente, quem recebe aviso, tipo, lista, uso do CRM, automações,
  teste). Estado ao vivo: "Drain & Wash Campaign - Replies" só punha tag + SMS/e-mail ao Mike (as 11 respostas de 19/10
  nunca viraram card); "SMS Customer Reply to pipeline" (reativação) já criava card em New Lead, mas o aviso ia só ao
  dono (Mike), sem e-mail, e a sequência de reativação seguia depois da resposta. A reativação ainda não foi enviada a
  ninguém (0 contatos com `reactivation`).
- `scripts/sf_campaign_replies.py` (plan/test/apply, backup dos 2 fluxos): Drain & Wash Replies + card New Lead (origem
  "SMS Reply - Drain & Wash") + tag `new lead`, SMS para Mike e Kris, e-mail para Mike e Kris; reativação: + "Stop
  reactivation sequence" (tira de Reactivation SMS/Email), SMS para Mike e Kris, e-mail para os dois. Ids dos passos
  existentes e alvo dos gatilhos mantidos; re-entry igual.
- Teste em cópias ZZ TEST (gatilho por tag; "Customer Replied" não dá para simular; sem SMS/app para o Mike/Kris,
  e-mails para o pedro@): resposta → card New Lead + tag, saiu da sequência; controle continuou; dw → card + tags;
  4 e-mails [TEST] chegaram. Contatos, cards e workflows de teste apagados. Respondido à Val; perguntei se crio cards
  para as respostas reais de outubro (ex.: Evan Harrison). Resposta "STOP" também vira New Lead (GHL põe DND).
  Tarefa 86bcygeub fechada.
- Basecamp: Frank me adicionou ao projeto "Capital Lawn & Pool" (só convite). A conta GHL continua esperando a private
  key + form do n8n (TODO 3).

## 04/11 (22h UTC) — inbox watch, 5 itens (gravação ao vivo bloqueada na sessão da rotina)

- **Clear Pool Tucson — ligação atendida virava perdida** (Derek via Frank, e-mail). Desde o "sem aperte 1" (27/10) o IVR
  começa com 2 passos comuns (tirar `ivr call missed`, tag `ivr pressed 1`) antes do Connect call; o motor do IVR começa
  no 1º passo de IVR → a tag nunca entra → "Route the call" mandava toda ligação para "Didn't press 1" (= perdida: SMS,
  card, tarefa, aviso). 29/10, 02/11 e 04/11: atendidas (IVR `completed` 34–46 s), todas com o SMS. Na NorTex a mesma tag
  vem depois do gather e funciona. `scripts/cp_ivr_answered_fix.py`: "Pressed 1" → "Reached Derek's phone" (sem tag
  `spam`, ou seja, todo mundo depois de spam/cliente); "Did Derek answer?" (`ivr call missed`) decide. Teste em cópias
  15/15 (atendida sem tag de IVR, não atendida, spam, cliente atendido/perdido × 3 fluxos), limpo. **`apply` bloqueado
  pela permissão da sessão** → Pedro roda/aprova. Frank respondido por e-mail. Tarefa 86bcyjmjh.
- **Bahama Blue — IVR** (Frank, DM). 3 linhas no "IVR SPAM Detection" (aperte 1 → Andy 10 s → recado). Não atendida não
  ganha `missed call` → "Missed New Lead - Initial SMS" nunca dispara; quem não aperta 1 cai em ~13 s sem nada. As 6
  ligações da conta foram assim (inclusive o teste do Frank hoje); só tag + card + tarefa do "Answered Incoming Call".
  Sobras: "AdWords Call In" com número de Tucson, "Sequential Call Routing" da BluVantage. Plano mandado ao Frank; tarefa
  86bcyjmmh.
- **Stay Fresh — respostas de Drain & Wash** (Val). 11 revisadas, nenhuma com card. Interesse: Susan Ogg, Evan Harrison,
  Brent Olson, Cyndy Pellien, Jen Knight, Donna Johnson; sem card: Toni Mason e Mike Haskell (STOP), Suzy Wright, Jason
  Hatch, Charlene Darst. Nenhum workflow dispara em New Lead (conferido). Falta criar os 6 cards + guarda de STOP nos 2
  fluxos de resposta. Val respondida; tarefa 86bcyjmq9.
- **Poolheads — páginas do Atif**: 3 páginas + 3 obrigado no ar (go.poolheadscare.com, 200), forms certos, (936)
  301-0309. Falta redirect dos forms (só o formAction da versão mais nova; o modo `thanks` do ph_ads_forms reconstrói o
  form) + teste real. Comentado na tarefa; minha tarefa 86bcyjmtp.
- **Pool Shack (Basecamp, cliente vê)**: Rob pergunta à Val sobre agency/client verification do Google Ads → rascunho por
  e-mail ao Pedro, não postado. Ledger: 5 linhas `needs_pedro`.

## 05/11 (12h UTC) — inbox watch, 17 itens

- **Blue Lagoon — "$250 Offer"** (Frank, DM, com o post da Caila de 19/10 no Basecamp, cliente vê). Origem: workflow
  "SMS Blast Campaign" (`e217a274…`), **draft desde 03/08**; últimos envios 01–03/08. Varri as 500 conversas com
  atividade desde 01/08: nenhum envio depois de 03/08. A Chiaro Anthony recebeu em 23/07 e respondeu "Stop" em 19/10,
  e a conversa subiu para o topo da caixa (parecia envio novo). Carmen Wood (11/10) foi resposta dela; a Destiny
  respondeu em 12/10. Nada alterado. Frank respondido no DM (ofereci apagar o workflow velho; aguardando ele).
  Rascunho para a Caila na tarefa 86bcyu05g (Pedro aprova e posta).
- **Clear Pool — fix do IVR (atendida virando perdida) aplicado**: `cp_ivr_answered_fix.py apply` às 12:05 UTC
  (backup `backup/clear-pool-solutions-tucson/workflow-*-20261105-12054*.json`), os 3 fluxos ainda publicados, re-entry
  on, gatilhos ok; `plan` = "já feito". Falta conferir em ligação real e depois confirmar ao Frank (thread "Fwd: IVR
  Issue"). Tarefa 86bcyjmjh em andamento.
- Sem ação: Pool Shack (a Val já respondeu ao Rob), resumo do Basecamp, Poolheads/Aqua Clear/Corolla mockups (site, com
  o Frank/Atif/Vikkar), Frank "Beautiful, thanks" e Pool Duck ("if you need anything", o plano está no TODO 2 do Pedro),
  thread das páginas Poolheads (Frank/Val/Atif, nada para mim; minha 86bcyjmtp segue aberta). Capital Lawn & Pool:
  e-mail do onboarding → falta a private key + form (TODO 3, needs_pedro).
- Sessão sem conector Gmail/n8n: não respondi ao e-mail do Frank, não mandei o rascunho por e-mail e não gravei o
  ledger. Tudo isso foi na notificação para o Pedro.

## 05/11 (13h UTC) — inbox watch, 2 itens (tarefa Poolheads - New Landing Pages)

- Frank → Val ("Yes please", mandar as 3 páginas ao cliente) e Atif → Frank (formatação do site corrigida): nada pedido
  a mim. Como as páginas vão para o cliente/anúncios, fiz a minha parte pendente (86bcyjmtp):
- **Forms → páginas de obrigado**: `ph_ads_forms.py thanks` agora só troca o `formAction` da versão mais nova (não
  reconstrói o form; `--only weekly|repair|leak`). Aplicado 12:47–12:48 UTC (backup `backup/poolheads/form-*-20261105-*`):
  WEEKLY → /thank-you-pool-service, REPAIR → /thank-you-pool-repair, LEAK → /thank-you-leak-detection. Diff vs backup =
  só a ação; o widget público (`/widget/form/<id>`) traz cada URL. As 6 URLs (as do funil e as `-page` da Val) embutem o
  form certo; obrigado = 200.
- Falta (mão humana, Turnstile): envio real em cada página → redireciona + contato/tags/card New Lead/aviso ao Felipe
  (avisar antes), depois apagar. Comentei na thread da Val; tarefa 86bcyjmtp em andamento.
- Sem conector Gmail/n8n nesta sessão: ledger não gravado (2 itens → done), passos para o Pedro na notificação.

## 05/11 (~14h UTC) — inbox watch, 1 item

- Val → eu ("awesome, TYSM") na thread das páginas Poolheads (86bcwet1g): agradecimento, nada pedido. Sem resposta.
  Pendente meu continua o mesmo (86bcyjmtp): envio real nas 3 páginas (Turnstile → mão humana) para conferir redirect,
  card New Lead e aviso ao Felipe, depois apagar; aí confirmo na thread. Ledger n8n sem conector nesta sessão
  (item cu-reply-90140278275905 → done, "thanks only").

## 05/11 (~14h30 UTC) — inbox watch, 1 item

- Basecamp Poolheads, "Google Ads" (Val → Felipe, cliente vê): apresentação da Val e as 3 páginas `-page` para o
  Felipe opinar. Nada pedido a mim, sem comentários na mensagem; não postei. Meu pendente segue o 86bcyjmtp (envio
  real nas 3 páginas → redirect/card/aviso, depois apagar). Ledger n8n sem conector (item 1a1abd4de2f47956 → done,
  "Val intro to client, no action").

## 05/11 (~15h UTC) — inbox watch, 1 item (Corolla, cliente vê)

- Basecamp Corolla "Website Mockup": Josh aprovou o site novo ("go ahead and publish"), leads caíram com o site Wix,
  vai manter o Wix ativo um tempo, pergunta se segura os pedidos de review no Google. Pergunta é para o Frank (site);
  não postei (cliente vê). Rascunho para o Pedro na notificação.
- Minha parte (GHL): o staging embute 2 forms da conta Corolla (`hhXkAONzl78btBsxb35f`): "Request a Quote"
  `Ft5UHxn2jwcJynAxLYBw` e "Main Contact Form" `w5MxiPRdTfGTww4aY4uV` (ambos mensagem, sem redirect). O
  "Website Form Fill To Pipeline" (publicado; card + avisos) só escutava o form antigo `zZVClfbhuG9LafXaMfN8` → lead do
  site novo viraria só contato. Incluí os 2 forms no gatilho `kJSLeNZg2JpJNON7heGg` (backup
  `backup/corolla-pool-and-spa/trigger-*-20261105-*` + workflow); relido: publicado, ativo, só a lista de forms mudou.
  Conta sem nenhuma submissão de form em 30 dias.
- Falta: envio real em cada form depois do go-live (Turnstile → mão humana), conferir card/aviso e apagar.
  Tarefa 86bcyw37n (em andamento). Ledger n8n sem conector (item 1a1ac1849e3f5d06 → done, "Corolla launch: GHL
  forms wired; reply is Frank's").

## 05/11 (~14h45 UTC) — inbox watch, 2 itens (Smart Chem Pools, mesmo pedido)

- Christopher Keplinger (web dev do site Lovable) por e-mail (cliente vê) e no chat Pool Profits: pede uma conta GHL
  para a **Smart Chem Pools** para ligar os forms do site. Nenhuma sub-conta com esse nome entre as 64 e nenhuma
  submissão no survey de onboarding (`efErcbOr4GAKXzZ28J4S`) → regra "Create GHL Account": nada criado.
- Respondi no thread do chat (interno): a conta nasce do form de onboarding, pedi ao Frank que mande o link ao
  cliente (ou diga se já foi preenchido com outro nome/e-mail). Tarefa 86bcywax9 (prazo 07/11, 2 h). E-mail do
  Christopher: rascunho na notificação para o Pedro aprovar.
- Sem conector Gmail/n8n: ledger não gravado (1a1ac255402111e1 e cu-chat-80140065683863 → needs_pedro).

## 05/11 (~15h15 UTC) — inbox watch, 1 item

- Frank no thread Smart Chem Pools (chat Pool Profits): "Yep will work on it today!" — vai mandar o link de onboarding
  ao cliente. Nada pedido a mim; sem resposta. Sigo aguardando o form de onboarding (regra "Create GHL Account");
  tarefa 86bcywax9 sem mudança. Ledger n8n sem conector (item cu-chat-80140065687644 → done, "Frank ack, no action").

## 05/11 (~18h UTC) — inbox watch, 4 itens (Frank, Bonneville)

- **DM "phone system requires configuration"** (print de Bonneville → Settings → Phone Numbers): a API confirma
  "No Twilio account found for location DeSfqW31OleIiU7eUt35" (sem LC Phone; rebilling off). Mandei ao Frank no DM o
  passo a passo (Agency → Settings → Phone Integration → LC Phone → ativar Bonneville; comprar número 801; A2P no Trust
  Center; site sem privacy/terms). Não encontrei o "processo" antigo que ele citou (ClickUp/repo). Tarefa 86bcz0y87.
- **Basecamp "📢 Client List"** (interno): formatar Customers (4).xlsx para importar. O conector do Basecamp não baixa o
  arquivo (nem o storage assinado, nem o e-mail) → comentei pedindo o xlsx no DM do ClickUp e se todos são clientes
  ativos (tag); formatar amanhã com `pp_import_clean.py` (xlsx → csv antes). Tarefa 86bcz0y7b.
- Ledger n8n: não há ferramenta de update → linhas novas com o mesmo item_id (3 done, 1 in_progress).

## 05/11 (~19h UTC) — inbox watch, 6 itens (Frank: Bonneville + Pool Shack)

- **Bonneville, lista de clientes** (DM + Basecamp "📢 Client List", interno): o xlsx (export do Skimmer, 149 linhas,
  Active/Inactive) baixou do DM. Novo `scripts/pp_import_skimmer.py` (só lê o GHL): telefone +1, endereço do serviço,
  tags `active client` + `existing customer` (ativos) / `past client` (inativos) + `skimmer import` + TagList; mesmo
  telefone/e-mail = 1 contato com os outros endereços em Notes; 37 indicações da **Blue Wave Spas** ("Blue Wave" no
  sobrenome + e-mail do revendedor drew@/melinda@bluewavespas.com: juntariam tudo num contato) → nome limpo, e-mail do
  revendedor em Notes, tag `blue wave referral`; linha "Schedule Available (4 jobs)" fora. Resultado: 88 importáveis
  (74 ativos, 14 antigos) + 55 sem telefone e sem e-mail (arquivo à parte). Enviados ao Frank no DM, comentário no
  Basecamp; ofereci importar (antes: conferir que nada publicado dispara em contato novo/tags). Conta com 0 contatos.
  Tarefa 86bcz0y7b (aguarda o Frank).
- **Pool Shack, "errors in the automations"** (print: "Website Form - Main Contact / Service Form" → inbound webhook
  "Mapping Reference is required"): `ps_site.py ghl-test` (cópias ZZ TEST, apagadas) 2/2 ok → o webhook funciona; o aviso
  é a falta de requisição de amostra salva no gatilho (só pela tela, depois de um envio real; nenhum envio do site
  chegou desde 03/11 — 0 contatos com `website form fill`). Varredura de 216 workflows: nenhum gatilho inbound_webhook
  guarda campo de mapping (fica fora do GET do gatilho).
  `pp_audit`: "AdWords Form - New Lead" com gatilho em form inexistente (`YAwhPHdh4TcKq158O6vm`, nunca disparou) →
  **draft** (backup `backup/the-pool-shack/workflow-6d3e4b75-*`; 6 passos iguais, re-entry mantido). "Add Task" com
  incompleteData (contact.assigned_user) = igual à Southern, tarefas são criadas → sem mudança. Respondi no DM.
  Passo humano por e-mail ao Pedro: envio real nos 2 forms do site (avisar o Rob) → escolher a requisição como Mapping
  Reference nos 2 gatilhos → eu confiro e apago. Tarefa 86bcz2gme.
- Ledger n8n: 6 linhas (5 done, 1 needs_pedro).

## 05/11 (~20h UTC) — inbox watch, 1 item (Frank, Pool Shack)

- DM com print de **"Website Form - Request a Quote"** (bolinha laranja no gatilho inbound webhook): mesmo aviso de
  "Mapping Reference" do Main Contact (já explicado no DM às 19h). Reconferido: 0 contatos com `website form fill` → nenhum
  envio real do site ainda. Respondi no DM (envio real nos 2 forms amanhã cedo → salvar a requisição como referência nos
  2 gatilhos → conferir card/aviso → apagar). Comentário na tarefa 86bcz2gme. Ledger n8n: 1 linha done.

## 05/11 (~22h UTC): inbox watch, 2 itens (Frank)

- **E-mail "Ekahi Solutions LLC - Automations"** (só o Frank): texto havaiano + sem links de agendamento + repensar
  o Monthly Service Reminder. Novo `scripts/ek_wording.py` (plan / `--apply` / `--test <inbox>`, idempotente, troca só o
  trecho e mantém o HTML): "Hi {{" → "Aloha {{" e "Hey {{" → "Howzit {{" nos 23 templates SMS; link de agendamento →
  "reply here or call/text us at {{business_phone}}" em Reactivation SMS 2 e Upsell SMS 2 (draft) e nos e-mails de
  Reactivation 1–3 (template + passo). Achado: 4 passos de e-mail (Nurture Day 2/3, Lost Stage 1/2) ainda mandavam o
  booking link, embora os templates já estivessem em "call or reply" → o passo agora tem o html do template. Backup em
  `backup/ekahi-solutions-llc/`; releitura 0 diferenças; status e re-entry mantidos (In Communication já estava com
  re-entry off). Re-dump: nenhum Hi/Hey ou booking_link na conta. Teste: prévia pela Test Snapshot para
  pedro@poolprofits.com (4 e-mails chegaram e foram conferidos; workflow/contato de teste apagados).
  Não conferido: o texto do review request nativo (configurações de Reputation, sem endpoint conhecido).
- Monthly reminder: não mudei a lógica. Respondi no thread com a proposta "first 90 days" (detalhes do dia de serviço →
  check-in depois da 1ª visita, no lugar do SMS de 1 h depois do Won → dica havaiana no dia 30 → filtro no dia 75 (o draft
  "Filter Clean Reminder") → check-in por trimestre), contra o lembrete semanal (vira ruído, e um STOP corta o SMS da
  review). Perguntei se o Erik usa app de relatório de visita (Skimmer). Montar em draft até 09/11 depois do ok do Frank.
  Tarefa 86bcz7706.
- DM do Frank "Thanks @Pedro G!": só agradecimento, sem resposta. Ledger: 2 linhas done.

## 05/11 (23h UTC) — auditoria semanal (`docs/weekly-audit-log.md`)

- **Clear Pool**: fix do IVR confirmado em ligação real (17:34 UTC, atendida 116 s → SMS "answered", card). Frank
  respondido no e-mail "Fwd: IVR Issue"; tarefa 86bcyjmjh fechada.
- **Stay Fresh**: `scripts/sf_stop_guard.py` — if/else "STOP reply?" (`contact_reply`/`message.body`: is-any-of palavras de
  opt-out + contém "unsubscribe") envolvendo a cadeia dos 2 fluxos de resposta; teste em cópia (caminho "Real reply" → card)
  ok, limpo; aplicado (published, re-entry igual). Lado STOP: teste real com o Pedro. 6 cards criados em New Lead (Susan
  Ogg, Evan Harrison, Brent Olson, Cyndy Pellien, Jen Knight, Donna Johnson; origem "SMS Reply - Drain & Wash"; nada
  dispara em New Lead nem na tag; só a atividade "Opportunity created"). Val e Frank (estatísticas do disparo: 105
  enviados 19/10, 103 entregues, 11 respostas) respondidos.
- **Bahama Blue**: `pp_ivr_missed.py --apply` (ramo "não atendeu" → `missed call`); "AdWords Call In - New Lead" (Tucson)
  e "Sequential Call Routing" (BluVantage) → draft (backup). Teste real com o Pedro (tarefa 86bcyjmmh).
- **pp_fix** (básico, backup + releitura): Wrigley, Sunwave, YardSpring, Precision, Simple, SwimReady, Signature, Clean
  Co, Corolla, Aqua Clear. YardSpring/Sunwave/Corolla/Aqua Clear com `--drop-booking` (calendários sem membro). 3 SMS de
  modelo com link de calendário ("New Lead SMS 2", "No Response SMS 1", "No-Show SMS 2") → "reply / call us" em
  YardSpring, Corolla e Aqua Clear. Corolla: `a2p_verification_number` = +1 252-600-3428 (número do GHL). Aqua Clear:
  Review Request com link de review da Clear Pool → `g.page/r/CZRcZF3HgnXLECE/review` (custom value dela).
- `_common.py`: `GHL_AGENCY` escolhe `dump/<agência>` no import (antes o dump da Pool Duck ia para `dump/`).
