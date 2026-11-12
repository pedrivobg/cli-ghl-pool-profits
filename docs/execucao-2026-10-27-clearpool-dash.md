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

## 07/11 — BluVantage: Homebuyer Postcard (Val, ClickUp 86bck0f6j)

- Páginas do Atif (funil "BluVantage - New Homeowner Welcome" `8K72QYlax9bCu7Asa15X`): landing
  go.bluvantagepools.com/new-homeowner-welcome---landing-page (página `BCsQYJZVHKONhfE4LXFj`) e obrigado
  /new-homeowner-welcome---thank-you (200). A landing usava o form do Atif "BluVantage — New Homeowner Welcome"
  (`mLGnkBqG0Zbrgjl4p41w`, 05/11): endereço em 5 campos, redirect para `…---thank-you-page` (também abre o obrigado),
  **nenhum workflow ouvindo** (0 submissões até hoje).
- `scripts/bv_homebuyer_form.py` (plan/test/apply):
  - Form **"Homebuyer Postcard Campaign"** `iljZOmWY2dAQiHi2NbAt` (da versão mais nova do form do Atif: visual, botão
    "Claim My Offer", os 2 consentimentos de SMS iguais aos nossos): First Name*, Last Name, Property Address* (um campo,
    busca do Google, como na NorTex), Email*, Phone* (seletor de país), → /new-homeowner-welcome---thank-you (os 2
    campos de redirect; regravado depois de criado). Submissão aparece na conversa; aviso por e-mail do form desligado.
  - Workflow **"Homebuyer Postcard Campaign - New Lead"** `3b3d2fb6-4a46-4ac0-9b8e-c57118c540f3`, publicado, re-entry on:
    Form Submitted = form novo **ou** o do Atif; cópia do "AdWords Form - Heater & Equipment Repair" sem a conversão do
    Google Ads (cartão postal, não anúncio) e sem Service Requested; if/else spam/dnd/current customer (o das ligações);
    texto aos 5 usuários + e-mail a vanessa@/paul@; tags `new lead`, `printed marketing materials`, `homebuyer postcard
    campaign`; card 💧 Pool Leads 💧 → New Lead, origem "Homebuyer Postcard Campaign"; o mesmo SMS de resposta ao lead.
  - Página: elemento `form-r7EGTC35lN8` → form novo (backup `backup/bluvantage-pool-service/page-BCsQYJZVHKONhfE4LXFj-
    20261107-140800.json`; salvo live; diff = só formId). Página ao vivo 200 com o form novo; print conferido.
- Teste (cópia ZZ TEST com gatilho de tag, só e-mail para pedro@): lead → 3 tags + card New Lead com a origem; spam → nada;
  current customer → nada. Contatos, cards, workflow e tag de teste apagados. Nenhum workflow escuta a etapa New Lead.
- Falta (mão humana, Turnstile): envio real na landing → redireciona + contato/tags/card + texto/e-mail à equipe (apagar).
  Form do Atif ficou sem uso (pode apagar). O telefone da página é 404-224-9387 (linha "Incoming Call"), não a linha
  "Printed Marketing Materials" 404-334-2495: ligações do cartão não ficam marcadas como postal (perguntar à Val).

## 07/11 — Pool Duck Franchising: SMS por etapa em Franchise Development (pedido do Lee)

- `scripts/pd_franchise_stage_sms.py` (plan / test / apply) + `config/pd_franchise_stage_sms.json` (textos do Lee).
  Remetente = número padrão da conta (Lee, 813-710-4144), como no Tampa Show. Pasta Franchise Drip Campaigns.
- 4 sequências, gatilho = card entra na etapa (`pipeline_stage_updated`, publicadas, re-entry on):
  - **Intro Call Nurture** `7c34c412-4f60-44fe-a7b1-c8b895ff1ca2` ← 📞 Intro Call Booked (o "Intro Call" do e-mail): SMS 24 h depois.
  - **Missed Intro Call** `3101d3fc-0992-4ccb-9c82-ddc50ee48228` ← 👻 Missed Intro Call: 20 min, +24 h, +2 dias
    (link `widget/booking/IiyQDitIIbOyigGsmAKt` = calendário "[MISSED] Franchise Introductory Call"). Stop on response.
  - **Webinar Nurture** `cd43a4fc-ceac-4575-8cfc-4629534dbb90` ← 🖥️ Webinar: SMS 24 h depois (vídeo Voices of Pool Duck).
  - **Missed Webinar** `3a0a765d-1b0d-4891-8238-174e02e38e31` ← 👻 Missed Webinar: 20 min, +24 h, +2 dias
    (`widget/bookings/franchisepresentation2`). Stop on response.
  - Toda espera segura o texto até 9h–20h ET. Cada sequência começa tirando o contato das outras 3.
- Saídas: **Missed Follow-up Stop (Booked)** `8010fe62-0ce9-4162-9a7c-65c9e33c1770` (agendamento confirmed/new em qualquer
  calendário → sai das 2 Missed); **Stage SMS Stop (Left Stage)** `c632979f-9e5e-4f14-aba1-5791460bb8ef` (card entra em
  qualquer uma das outras 20 etapas, ou won/lost/abandoned → sai das 4). Resposta (inclusive STOP) = `stopOnResponse`
  nativo nas 2 Missed; DND o GHL já não manda SMS.
- Textos literais; mudanças: "here here" → "here"; SMS 2 do Missed Intro dizia "re-schedule your call below" sem link →
  link do SMS 1/3 no fim. Sem texto de opt-out (literais do Lee; ver STOP do Tampa).
- Teste (cópias ZZ TEST com gatilho filtrado por tag de teste, esperas de 1–2 min, tag no lugar do SMS, contatos sem
  telefone): 8/8 ok — New Lead → Intro Call; card criado direto em Webinar também dispara o `pipeline_stage_updated`
  (por isso não há gatilho `opportunity_created`: inscreveria duas vezes); Missed Intro completo (3); agendou depois do
  SMS 1 → parou; Missed Webinar → Unit Economics → parou; Missed Webinar → Intro Call Booked → parou e entrou no Intro
  Nurture; card abandoned → parou; saiu e voltou para Missed Intro → recomeça (re-entry). Resposta não simulável
  (inbound 401). Tudo apagado (workflows, contatos, cards, tags).
- Só cards que se moverem daqui em diante entram (os 45/13/8/2 que já estão nas etapas não).

## 07/11 (~14h UTC) — Stay Fresh: cards orçados em Quote Sent sem follow-up + "Service Needed" no form do site (Frank, e-mail 06/11)

- **Quote Sent sem mensagem** (`scripts/sf_quote_sent_silent.py` plan/guard/test/apply/check): a varredura de todos os
  gatilhos da conta mostra só o "Quote Sent Follow-up" reagindo à etapa 💰 Quote Sent (o "Stop Follow-ups" não escuta essa
  etapa). Guarda **permanente** (mesmo formato do `existing customer` nos Won): gatilho `3M0Uh4HpGV5UDzdewSzo` + filtro
  "Doesn't Have Tag: `quoted manually`" (backup `backup/stay-fresh-pools/trigger-3M0Uh4HpGV5UDzdewSzo-*`; tag criada).
  Uso pela equipe: pôr a tag e depois mover o card. Teste (cópia ZZ TEST com o mesmo gatilho + "has zz tag", 2 contatos só
  com e-mail): com a tag o card foi para Quote Sent e não entrou; controle entrou. Tudo apagado (o controle tirado também do
  fluxo real, que espera 1 dia antes do SMS 1).
  Aplicado em Donna Johnson, Cyndy Pellien, Brent Olson ("Bret Olsen"), Evan Harrison, Susan Ogg (cards New Lead de 05/11) e
  **Sean Mullane** (já tinha card New Lead do form do site de 30/10, página pool-resurfacing): backup do card → tag → PUT
  etapa → 90 s → remove do Quote Sent Follow-up por garantia → tag tirada (re-orçamento futuro segue o fluxo normal).
  Conferido: 6 cards em Quote Sent (open), nenhuma mensagem de saída desde o apply (só a nota de atividade type 28
  "Opportunity updated" — não é mensagem). Reconferir depois de 08/11 14:10 UTC: `sf_quote_sent_silent.py check --since 1794060485784`.
- **"Service Needed" + roteamento** (`scripts/sf_service_routing.py` plan/test/apply/style):
  - Campo `contact.service_needed` (dropdown: Weekly Pool Service, Pool Repairs, Pool Remodeling, New Pool Build, Other).
  - Form do site = **Main Website Form** `kqNJs6ZFliL5IQQpUYp6` (7 das 9 submissões de 2026, todas de stayfreshpoolsaz.com;
    "FORM - GOOGLE ADS" só no go.stayfreshpoolsaz.com, última em 08/2026; os outros 3 forms do gatilho sem submissões).
    Dropdown obrigatório antes de Message (versão mais nova lida antes do POST, `keep_redirect`, ação "mensagem" igual).
    O CSS próprio do form não estilizava o componente dropdown (caixa branca + borda do input de busca escondido) → bloco
    de CSS no fim do customStyle (`style`); print headless conferido (mesma borda dourada/placeholder dos outros campos;
    a lista aberta não foi conferida em print).
  - "Website Form Fill To Pipeline": if/else "Service Needed?" no início: Weekly → dono Kris → card (dono Kris) → tags → SMS
    Kris → e-mail Kris → FYI por e-mail ao escritório (Mike) → tarefa Kris; Repairs/Remodel/Build/Other → dono Mike → card →
    SMS Mike → e-mail stayfreshpoolsoffice@ → FYI e-mail Kris → tarefa Mike; sem serviço (outros forms, gatilho por tag) →
    cadeia antiga com os mesmos ids (SMS aos dois, e-mail Kris). Published, re-entry true, 2 gatilhos no if/else. Backup.
  - "Contact Created -> add owner": `only_unassigned_contact` false → true (corrida: rodando depois do form, devolveria o
    Mike como dono de lead semanal). Contato sem dono continua indo para o Mike.
  - Achado: os cards do form do site saíam **sem dono** (Sean Mullane: `assignedTo` vazio), o card nasce antes do
    "add owner". Nos 2 ramos novos o dono é posto antes do card.
  - Teste: cópia ZZ TEST (gatilho por tag, sem SMS/tarefa, e-mails para pedro@, os 2 ramos atribuindo Mike para o Kris não
    receber nada, tag-marcador por ramo), 6 contatos (5 opções + vazio): 6/6 no ramo certo, 1 card em New Lead, dono do card
    = usuário atribuído; 11 e-mails chegaram em pedro@poolprofits.com com "Service: …" preenchido. Tudo apagado.
  - If/else `contact_detail` com id do campo SINGLE_OPTIONS e `==` no texto da opção funciona (testado).
- Falta mão humana (Pedro): envio real no site (Turnstile) — "Weekly Pool Service" → dono/card/tarefa Kris, SMS+e-mail Kris,
  FYI no escritório; depois "Pool Repairs" → Mike. Os avisos vão de verdade para o Kris/Mike (avisar antes) e o card/contato
  de teste é apagado depois. Abrir a lista do dropdown no site para ver o estilo.

## 07/11 (~14h UTC) — Ekahi: Monthly Service Reminder pausado + "First 90 Days" em draft (Frank, e-mail 06/11)

- Frank aprovou (06/11): pausar o lembrete mensal e montar a sequência dos primeiros 90 dias em draft. Erik já usa o
  Skimmer e manda relatório de visita → a sequência não manda relatório. Novo `scripts/ek_90day.py` (`pause` / `build
  [--apply]` / `test`); textos para o Frank em `docs/ekahi-90-day-sequence.md`.
- **Monthly Service Reminder** (`86c93caf…`) → **draft** (backup `before-pause`; releitura: passos iguais, re-entry
  igual, gatilho inativo). Era 1 SMS 30 dias depois de Recurring Customer.
- **First 90 Days - New Client Sequence** (`2a9188d0-c59e-458d-a49c-d7b90bd9e640`, DRAFT, pasta 04 Pipeline
  Automations, re-entry off): gatilho Pool Leads/Won (o mesmo do Won Stage / Post-Appointment / Review Request). Tag
  `first 90 days` → +1 h SMS Day 1 (gate code, pets, melhor contato) → dia 7 SMS "como foi a 1ª visita" → dia 30 SMS
  dica havaiana (chuva/sol/trade winds) → dia 75 e-mail do filtro (texto do draft "Filter Clean Reminder" com Aloha e
  reply/call/text) → a cada 90 dias SMS de check-in sazonal (Go To em loop). Antes de cada mensagem: if/else "Still a
  client?" (sem `lost lead` / `spam` / `dnd` / `one-time customer`). Esperas seg–sex 9–17h (Pacific/Honolulu). 5
  templates novos "90 Days - …" (4 SMS + 1 e-mail). Dia 14 = Review Request, sem mudança. Sem link de agendamento.
- Ao publicar (não feito): tirar o "SMS 1" do Post-Appointment Follow-up (1 h depois do Won, "pool service today") e
  trocar a espera de resposta dele por espera de 2 dias (tags e ida para Recurring continuam); Filter Clean Reminder e
  Monthly ficam em draft.
- Teste (cópia "ZZ TEST …" na conta, esperas de 1 min, tag no lugar de SMS/e-mail, contato sem telefone): caminho
  completo em 402 s (dia 1 → 7 → 30 → 75 → trimestral) ✓; Go To: o check-in trimestral volta na volta seguinte ✓;
  guarda: com `lost lead` a mensagem não sai ✓. Contato, cópia e tags `zz90 *` apagados.
- Achado: gatilho criado num workflow em draft fica `active: true` (re-salvar em draft e PUT com `active: false` não
  mudam). Testado com cópia ZZ TEST: o workflow em draft **não** inscreve o contato mesmo assim (apagado depois).
- Falta: revisão do Frank (textos) → publicar + ajustar o Post-Appointment. Tarefa 86bcz7706.

## 07/11 — recuperação da sexta (créditos acabaram 06/11: a rotina recebeu 42 itens e não executou nada)

- Revisados os 42 itens do ledger (06/11). Feito hoje (detalhes nas seções acima de cada frente):
  Stay Fresh (6 leads → Quote Sent sem follow-up; dropdown Service Needed + roteamento Kris/Mike), Ekahi (lembrete
  mensal pausado; "First 90 Days" em draft, textos ao Frank), Pool Duck Franchising (4 automações do Lee publicadas;
  resposta ao Lee = rascunho no Gmail para o Pedro aprovar), BluVantage (form "Homebuyer Postcard Campaign" + workflow +
  form na página do Atif), Pool Keepers (`pp_client_sheet.py`, folha de 8 páginas M1–M23 enviada ao Frank + achados).
- YardSpring: os 3 números sem encaminhamento, sem usuário e sem IVR → a ligação do Google Ads de 04/11 não tocou para
  ninguém (Joe tinha razão). Perguntei à Val para qual telefone encaminhar; encaminhamento só pela tela (86bd02rg2).
  Outras contas com linhas sem encaminhamento/IVR listadas na tarefa (a confirmar se são usadas).
- Ledger: 42 linhas novas (39 done, 3 needs_pedro: Puddle Jumper, Capital Lawn, rascunho do Lee). Tarefas: 86bd02rg2,
  86bd02rg6 (testes reais), 86bd02rg9 (Pool Keepers), 86bcz7706 atualizada.

## 09/11 — inbox (4 itens): Ekahi (Erik respondeu), Pool Keepers FYI, digest

- **Ekahi** (Basecamp, cliente vê): Erik pediu (1) recomendação sobre o "Reply STOP" e (2) alternativa ao e-mail do dia 75
  (quase todas as piscinas dele são de areia, backwash mensal). Rascunho da resposta enviado ao Pedro por e-mail para
  aprovar: STOP só no check-in trimestral (sai do dia 30); dia 75 = A check-in de equipamento (areia a cada 5–7 anos,
  bomba/aquecedor; recomendado), B pedido de indicação, C tirar o dia 75. Nenhuma mudança no GHL (sequência segue draft).
  Depois da escolha: trocar o template "90 Days - Day 75…" (e o texto do dia 30), testar na cópia ZZ TEST, publicar +
  ajuste do Post-Appointment. Frank respondido no e-mail. Tarefa 86bcz7706 (prazo 11/11, 1 h).
- **Pool Keepers**: Frank mandou a folha M1–M23 ao Nathan antes da call — só FYI. Digest do Basecamp: nada pedido.
- Ledger: 4 linhas (3 done, 1 needs_pedro).

## 09/11 (~12h30 UTC) — inbox: Val "set everything to Joe" + conferir avisos das contas novas

- Val (DM ClickUp) respondeu à pergunta da YardSpring: tudo para o Joe; e pediu checar avisos de Pool Shack, YardSpring,
  NorTex e Pool Duck LWR. Novo `scripts/pp_notify_map.py <loc>` (só leitura: linhas, usuários e quem recebe cada aviso
  em todo workflow publicado). Correções em `scripts/pp_notify_fix.py ys|lwr [--apply|--test]` (backup antes do PUT).
- **YardSpring**: os avisos de Ads/LP/lead form já iam para o Joe (SMS + e-mail + tarefa), contato novo → dono Joe.
  "Website Form Fill To Pipeline" só fazia card + tarefa → **SMS "NEW LEAD - Website Form" ao Joe** depois da tag (mesmo
  passo da NorTex/Pool Shack). "Sequential Call Routing" (cópia da BluVantage: Fred/Paul, números e recado da
  BluVantage) estava publicado → **draft**. As 3 linhas seguem sem encaminhamento → passo do Pedro (tela) enviado por
  e-mail: encaminhar para +1 770-615-7665 + ligação de teste.
- **Pool Duck LWR**: "Google AdWords - Qualified Lead (Call In)" (linha 941-541-5942, sem encaminhamento/IVR) fazia card
  + tags e não avisava ninguém → **SMS "NEW GOOGLE ADS CALL" a Kenton + Pool Duck Service**. Perguntei à Val para onde a
  linha deve tocar. Ainda: fluxos antigos "… - Steve" / chat widget sem destinatário (ver se são usados).
- Pool Shack (tudo → Rob, linhas encaminham para 480-798-2888) e NorTex (tudo → Fareed, linhas no IVR): nada faltando.
- Missed-call text nativo ligado em YardSpring, NorTex e LWR (na YardSpring é o único text-back): não mexi.
- Teste: cópia ZZ TEST de cada cadeia nova (gatilho por tag, alerta/card/tarefa trocados por tags), contato
  @example.com: ✓ nas duas contas; contato, cópias e tags `zz notify test*` apagados. Releitura: status/re-entry iguais,
  gatilho ativo. Tarefa 86bd02rg2 (in progress). Ledger: 2 linhas (1 done, 1 needs_pedro).

## 09/11 — inbox: Poolheads landing pages (Atif → Val)

- Comentário do Atif na tarefa 86bcwet1g perguntando à **Val** se o cliente já respondeu sobre a página Pool Repairs
  (áreas atendidas + imagem de fundo, aguardando o Felipe). Nada pedido a mim: sem resposta, sem tarefa nova, sem
  mudança no GHL. Ledger: 1 linha (done).

## 09/11 — inbox: Frank "Sounds great" (Ekahi)

- Resposta do Frank ao meu e-mail sobre o Ekahi: só agradecimento, nada pedido. Sem resposta, sem mudança no GHL.
  Ekahi segue aguardando o Pedro aprovar o rascunho para o Erik (tarefa 86bcz7706, prazo 11/11). Ledger: 1 linha (done).

## 09/11 — inbox: Val (LWR linha do Ads no menu + checklist padrão), Poolheads LP (Atif ↔ Val)

- Val (DM): a linha do Google Ads da LWR (+1 941-541-5942, hoje não toca ninguém) deve passar pelo menu principal da
  Pool Duck, como a 941-588-2227. Novo `scripts/pd_lwr_ads_ivr.py plan|apply` (soma o número ao "Start IVR Trigger" do
  "Active - Phone Tree IVR", backup + releitura; mesmo padrão do `bv_call_numbers.py`). Plan ok; o **apply foi bloqueado
  pela permissão da sessão automática** → nada gravado. Passo do Pedro por e-mail: rodar o apply (ou tela) + ligação de
  teste. O "Google AdWords - Qualified Lead (Call In)" (call_status na linha) segue avisando Kenton + Service com IVR.
- Val pediu checklist padrão por cliente a cada form novo / antes de campanha → `docs/client-setup-checklist.md`
  (telefones/IVR, avisos, atribuição, forms/LP/lead form, tracking, workflows copiados, teste). Respondido no DM.
- Poolheads LP (86bcwet1g): Atif ↔ Val, nada pedido a mim.
- Tarefa 86bd02rg2 atualizada. Ledger: 3 linhas (2 done, 1 needs_pedro).

## 09/11 — inbox: Val (lista de clientes + agradecimentos)

- Val (DM): passou a List View de clientes (`2kyd9h1f-2894`) com datas de ativação, atualizada todo dia; nenhuma
  ativação hoje/amanhã. Respondi no DM que vou acompanhar a lista. Os outros 2 itens eram só agradecimento.
  Sem tarefa nova, sem mudança no GHL. Ledger: 3 linhas (done).
- 09/11 (2º lote): Val (DM) "awesome!!!! TYSM!!!" — só agradecimento depois da minha resposta; sem resposta, sem
  tarefa, sem mudança no GHL. Ledger: 1 linha (done).

## 09/11 — Contas novas: West Coast Pool Care (`63COocPIEK6XLvRikVK9`) e Capital Lawn & Pool LLC (`0FSiPPwFKaeanOv7FUIg`)

Roteiro novo: `docs/new-account-review.md`. As duas nasceram do snapshot antigo (`9VNEhn…`, sem o Refresh), como a
Bonneville. Backups em `backup/west-coast-pool-care/` e `backup/capital-lawn-pool-llc/`.

- **Survey**: West Coast `6aefe02d…` (08/11, Milen Der Nigoghossian, Montebello CA); Capital `6aebf1a2…` (05/11, Zuriel
  Jackson; a de 21/10 é de outro form). `pp_onboarding_fill --timezone`: Sao_Paulo → America/Los_Angeles; preços
  "null" → vazio (+ Logo URL "null" na Capital).
- **Custom values** (backup): Friendly Business Name "West Coast Chemical Company" (nome do site e do GBP; legal fica West
  Coast Pool Care) e "Capital Lawn & Pool" (site); Service Area "Los Angeles County, the San Gabriel Valley & Orange
  County" (era o texto do survey) e "Sacramento" (vazio); `a2p_verification_number` provisório = telefone do negócio
  (323) 695-6810 / (916) 585-0360 (nenhuma tem número no GHL). Missed-call nativo desligado nas duas.
- **West Coast sem usuário nem representante** (o painel não tinha nada): criado Milen Der Nigoghossian
  (`GBKrP2QIC3nh8bCdsNy1`, admin, permissões do admin da Capital, westcoastchemicalco@gmail.com, +1 323-767-6028 do survey)
  com `pp_add_user.py --like-loc` (opção nova) e posto como `authorizedRepresentative` do Business Profile (CEO).
  Capital: Zuriel Jackson já era usuário e representante.
- `pp_mirror --apply` (11 do modelo; Capital com Review Request publicado e place `ChIJaz4i-rceSC0RRLfNYqHAq4k` do
  g.page do survey; West Coast: `share.google/…` não resolve para place → Review Request draft), `pp_forms` (nada),
  `pp_nps` (NPS Form + link), re-dump, `pp_fix --drop-booking --include-drafts --skip "In Communication Stage"` (nada),
  `pp_tags_missing` ("form fill"), `pp_skip_tag` (já tinha), `pp_line_tag` (sem números; agora não quebra com "No Twilio
  account"), `pp_review_fix` (nada).
- Sequential Call Routing (BluVantage) e AdWords Call In (gatilho em Tucson) já em draft: genéricos/sem gatilho com
  `pp_master_cleanup.py --loc` (opção nova: só os 2 workflows, funis intocados). Funis "Simple Pool Care"/"LP Teste"
  ficam (como na Bonneville).
- Teste: contato ZZ TEST (@example.com, sem telefone/tags) em cada → dono = Milen / Zuriel; apagados.
- **Resultado**: auditoria 0 ALTA nas duas (MÉDIAs iguais às do modelo); `pp_ready` 0 ERRO (West Coast: 1 aviso,
  Review Request draft; Capital com `--place`).
- Telefonia: West Coast "No Twilio account" (LC Phone não ativado); Capital com Twilio e 0 números. Sites sem privacy/
  terms (404) → A2P pelo funil "New A2P Verification". Calendários inativos sem membros (booking tirado, padrão).
  Passos do Pedro no TODO 3.

## 09/11 — inbox: Val (número do Ed + weekly meeting)

- Val (DM): o número "Ed's number" da YardSpring (678) 448-5005 não é usado → fica sem encaminhamento (nada gravado no
  GHL). Weekly meeting mudou para 12h (horário dela) com link do Zoom às 12h02 BRT → push para o Pedro entrar.
  Respondi no DM. Sem tarefa nova. Ledger: 3 linhas (1 done, 2 needs_pedro).

## 10/11 — Corolla: respostas do guia do CRM (`hhXkAONzl78btBsxb35f`)

- Conta ainda no V9 antigo (sem o pp_mirror): o guia mostra o master; o que está no ar é outro (Incoming Call em toda
  ligação + tag `new lead` → SMS "We received your request…", No Response só por tag `follow-up` (sem etapa), 1 etapa Won,
  Review Request 14 dias). Publicados que o master tem em draft: Appointment Confirmation/Reminders, Post-Appointment
  Follow-up, In Communication Stage, Filter Clean Reminder, Monthly Service Reminder, Upsell Opportunity (não mexi).
- Sequential Call Routing (molde da BluVantage: 6 números dela, Fred/Paul, caixa postal dela; o número da Corolla não
  estava ligado) → draft. Janelas de envio → todo dia 08–18 (horário do cliente): Won Stage "Wait 2 minutes", Lost Stage
  2 esperas, Review Request "Wait Before NPS Request". Review Request: link do Google da Clear Pool Tucson → place da
  Corolla `ChIJ08hxEB6E04AReOkRA0DoxeU` (do `google_review_link`). Backups `backup/corolla-pool-and-spa/workflow-*-20261110-191729.json`;
  relido: status/gatilhos/re-entry iguais, só esses nós mudaram. Re-entry de No Response / Quote Sent já estava ligado.
- No pp_mirror da migração: Won Stage e Review Request voltam ao modelo (seg–sex 9–17) → reaplicar 08–18; boas-vindas de
  reparo (decisão 5) = rascunho para o Pedro aprovar, entra no ramo Repairs / Installs do Won Stage do modelo.

## 10/11 (~20h UTC) — Corolla: migração para o modelo (Pedro aprovou; guia do CRM aprovado pelo cliente)

- Conta com 0 contatos e 0 oportunidades (conferido por `/contacts/search` e `/opportunities/search`; a mesma chamada na
  Southern devolve 45) → nenhum card movido, nenhum envio a cliente real.
- `pp_mirror --apply`: pipeline Pool Leads 9 → 13 etapas (ids das 9 mantidos; "🏆 Won" → "🏆 Won - Weekly Pool Service";
  novas: No Response - Follow Up, No Show, Won - One Time Repair or Install, Won - Pool Construction or Remodeling);
  11 workflows copiados do modelo (Answered Incoming Call criado; Incoming Call / New Lead SMS renomeados para Missed);
  8 templates SMS com o texto do modelo; tag `missed call`; os 6 extras (Appointment Confirmation/Reminders,
  Post-Appointment Follow-up, In Communication Stage, Filter Clean Reminder, Monthly Service Reminder, Upsell
  Opportunity) → draft. Custom values da Corolla intactos.
- Sequência: `pp_forms` nada a fazer (5 forms de lead já no Website Form Fill); `pp_nps` (campo NPS Message, NPS Form com
  os campos da conta, `nps_survey_link`); `pp_fix` (AdWords Call In - New Lead, draft: "Clear Pool Solutions Tucson" →
  friendly name); `pp_tags_missing` 5 tags criadas (2ª leitura 0); `pp_skip_tag` filtro em 2 drafts; `pp_line_tag` →
  "Website & GBP Call - Tag" publicado (+12526003428); `pp_master_cleanup` (Sequential Call Routing sem Fred/Paul/números
  da BluVantage; AdWords Call In sem o gatilho do +15207771392); `pp_review_fix` nada. Missed-call nativo → off.
  Custom values `'null'` → vazio (Weekly Service / Chemical Only / Green to Clean Price).
- Janelas 08–18 todo dia reaplicadas: Won Stage "Wait 2 minutes" e Review Request "Wait Before NPS Request" (id novo
  `3f3826e2…` depois do espelho); Lost Stage não é espelhado e continuou 08–18.
- Boas-vindas de reparo (textos aprovados pelo Pedro): Won Stage, ramo Repairs / Installs, depois de "Mark won (Repairs /
  Installs)": "Repair Welcome Email" (html no passo + snippet "Won Stage - Repair Welcome Email" `MF4qSWIMMMFdeQEQ5zGd`)
  → "Wait 2 minutes" (todo dia 08–18) → "Repair Welcome SMS" (snippet `clUf03Y54apsohJXxObx`). Relido: só os 3 passos
  novos + o `next` do Mark won; demais ramos, status, re-entry e os 3 gatilhos iguais.
  **Atenção:** um novo `pp_mirror --apply` na Corolla volta o Won Stage ao modelo (apaga o ramo novo e as janelas 08–18).
- Conferido: `pp_audit` 0 ALTA / 8 MÉDIA (4 Add Task incompleto + 3 Won/Review mesmo gatilho do modelo + Landing Page
  form no Website Form Fill, sem workflow de Ads publicado); `pp_ready --place corolla-pool-and-spa=ChIJ08hxEB6E04AReOkRA0DoxeU`
  0 ERRO (sem o `--place` acusa o link de review porque o GBP não está conectado). Josh = único usuário: tarefas
  (`contact.assigned_user`) e avisos (assign/all/user) caem nele. ZZ TEST (@example.com, sem telefone) → dono = Josh em
  10 s; apagado. Backups em `backup/corolla-pool-and-spa/`.

## 10/11 (noite) — Frank: dashboard da reunião, gate de nota e todas as contas no modelo
- **Dashboard** (o da SwimReady): "Pool Profits Dashboard" na Snapshot Pool Profits e padrão em 56 contas (`pp_dashboard.py`;
  rota `duplicate` com `targetLocationId`, cópia vem privada → permissions → set-default). `pp_new_account.py` faz nas novas.
- **Gate de nota**: só 5 vai ao Google; 1–4 recebe "SMS - Ask What Went Wrong" + aviso à equipe (`pp_review_gate.py`).
  Antes o 4 ia ao Google (`!= 5 e != 4`). Teste na Test Snapshot (notas 4/5/2, contatos e workflow ZZ apagados). Aplicado no
  modelo, na master e em 25 contas; `config/snapshot_guide.json` atualizado.
- **Contas vs modelo** (`pp_fleet_check.py`, `reports/fleet-20261110.json`): 16 OK. Migradas hoje: Corolla, Aqua Clear
  (+ usuário Alex Kalogianis, dono no Contact Created; 0 ALTA/0 ERRO com --place), YardSpring (0/0), Bluebird e Summer Wave
  (`--no-publish`, pré-go-live). `pp_master_cleanup --loc` agora só tira gatilhos com números de outros clientes (Bluebird
  e YardSpring têm linha própria no AdWords Call In); `pp_mirror` tira "Remove from Workflow" de fluxos que a conta não tem.
- **Pool Smart OC** meio migrada (antes do critério): pipeline do modelo, 7 fluxos criados, Incoming Call/SMS Reply com
  passos do modelo; Missed New Lead SMS, No Response, No-Show, Quote Sent e Won Stage em **draft**; o Review Request antigo
  segue publicado. Faltam owner_first_name, business_phone, weekly_service_price, booking_link, google_review_link.
- **Não migradas (pré-V9, pipeline "💧 Pool Leads 💧", faltam 6–9 dos 9 custom values do V9 → SMS sairiam com campos
  vazios)**: ABC, Big George's, Clear Conceptz, Leisure, Premier 1 (2), PoolReady SELA, Signature, Net Positive, Legion,
  GID, Dream, JM, Next Level, Damon's, Clean Co, Blue Lagoon, SwimReady, Pooly, Ponchos, Pool Time, Pooltexx, Sparkling
  Clear, Precision, Reign, Wrigley's, Simple, Orange Tree. Além disso: Incoming Call por linha/IVR (SwimReady, Blue Lagoon,
  Reign com IVR SPAM Detection; 6 contas ouvem +18179548486, linha velha do snapshot), e-mails da Vanessa dentro do
  Website Form Fill da Orange Tree, sem usuário (Net Positive, Next Level, Pooly, Ponchos), `location_dirs` casa por
  pedaço do nome (Damon's pega a Billing Only). Planos em `scratchpad/fleet/`.
- **Fora por configuração própria**: BluVantage, Clear Pool Tucson, Ekahi, Sunwave, Pool Palooza, Golden View, Pool Duck.
## 10/11 — Rodada diária de contas novas (`daily-newaccounts-2026-11-10`)

- `pp_new_account.py --scan --apply --submit` (9 contas dos últimos 30 dias): Blissful Waters `A2P Verification Number` →
  (210) 864-9642 (número do GHL). Nenhum envio de A2P: todas esperam o go.<domínio> no site "New A2P Verification".
  Sem número disponível no DDD: Cleverblu (407) e Blissful (210) para as linhas 2 e 3.
- **Bug corrigido**: na Poolheads (já com nomes próprios, "Website & GBP"/"Google Adwords") o script rotulou as 2 linhas
  antigas sem nome — o principal 936-314-9255 virou "Facebook Ads". Voltei os dois nomes para vazio (encaminhamento do
  9255 → Felipe intacto) e o script agora só nomeia em conta sem nenhum nome ou número que ele mesmo comprou.
- `pp_dump` + `pp_audit` + `pp_ready`: 0 ALTA em todas; 0 ERRO nas 8 novas (Blissful, Bonneville, Capital, Cleverblu com
  `--place` do `google_review_link` da conta). Poolheads: ERROs são os drafts/fluxos da conta antiga (combinado, fora daqui).
- Guia do CRM publicado e aberto (200, sem erro de JS): Cleverblu, Blissful Waters, Rosebrook, WP Pools, Bonneville
  (`config/crm_guide_links.json`) → DM ao Frank. Comentário de status nas 5 tarefas "Create GHL Account" (Capital/West
  Coast já comentadas hoje, sem mudança). Sem e-mail novo: os 1ºs números já estão no [Passo seu] de hoje.

## 11/11 (~12h UTC) — inbox: dashboard com relatório da SwimReady (Frank), listas de clientes, rodada diária
- **Dashboard padrão (Frank: "this reporting pulled over")**: a cópia do "Pool Profits Dashboard" (origem SwimReady) traz 2
  widgets `object-embed` com links fixos da SwimReady — "Local Heat Map" (app.localdominator.co, taskId=70004) e "Local
  Reporting" (local-marketing-reports.com/…e934480d…) → toda conta mostrava o relatório local da SwimReady. O Frank tirou
  à mão em ~25 contas (Ekahi e NorTex com heat map próprio). `pp_dashboard.py`: origem agora = cópia limpa da Smart Chem
  (`6af374b6221fe50f64ae0b4c`, 14 widgets) e o plano acusa `FOREIGN EMBEDS` → 33 contas + a master ainda com os embeds.
  Remoção de widget por API sem endpoint conhecido (não chutei); pedido ao Pedro: aprovar apagar+recopiar ou tirar na tela;
  master antes do Refresh do snapshot. Também: preferência do widget GMB com `pageId` = place da SwimReady em todas
  (`ChIJS_4iU3DDGgoRbPjauVQYjNE`). Tarefa 86bd1ne8w.
- **Listas de clientes** Bahama Blue (xlsx) e Smart Chem (csv) no DM: anexo de chat não baixa pelo conector → pedi ao Frank
  para anexar na tarefa 86bd1ne90 e dizer se são todos ativos.
- **Rodada diária**: o commit de 10/11 (`32e2685`, guias do CRM de 5 contas + correção dos nomes de linha) estava só no
  branch `claude/sharp-albattani-qgcnif` → trazido para cá. O scan de hoje rodou antes disso e rotulou de novo 2 linhas da
  Poolheads (+19362431724, +19363149255): voltei para vazio (backup `backup/poolheads/twilio-20261111-before-revert`,
  encaminhamento igual); com a correção o scan não mexe mais. Nenhuma conta nova, nenhum A2P enviado (todas esperam o
  go.<domínio>); Corolla e Aqua Clear: brand APPROVED / campanha VERIFIED (Aqua Clear: +19282397997 sem encaminhamento).
- Pool Palooza (Todd, Basecamp, cliente vê): página Catalina Foothills pedida ao Frank/Val (site) — não é meu.
- Pool Duck (Frank quer conversar hoje): plano `docs/poolduck-snapshot-plan.md` espera a revisão do Pedro (e-mail [Passo seu]).

## 11/11 (~15h40 UTC) — Pedro: "1. aprovado (padrão p/ snapshot)", "4. anexado aqui"
- **Dashboard**: conferido ao vivo — 56 contas de cliente + master Snapshot Pool Profits com exatamente 1 "Pool Profits
  Dashboard", padrão, 14 widgets, sem embed da SwimReady (cópias novas criadas 15:27–15:32 UTC, logo após o OK).
  `pp_dashboard.py --apply --replace`: cópia limpa nova como padrão primeiro, depois DELETE da antiga (backup lista +
  detalhe). Tarefa 86bd1ne8w fechada; Frank avisado no DM. Master limpa → o próximo Refresh do snapshot leva a versão limpa.
- **Listas de clientes** (anexos do e-mail): `scripts/pp_client_list_import.py` (plan/--apply; upsert sem tags + POST tags
  `client list import` + `active client`/`existing customer`, inativo `past client`). Bahama Blue 28 (27 ativos, 1 past;
  City/State/Zip em colunas próprias — o `pp_import_clean` perdia isso e juntava linhas sem nome); Smart Chem = export do
  GHL antigo (ids de outra agência, 401), 63 contatos, fora 3 testes + 2 telefones inválidos. Nada publicado reage às
  tags (só "Contact Created -> add owner"). Importação em conta de cliente não rodou daqui (precisa de OK) → e-mail
  [Aprovar]. Tarefa 86bd1ne90.

## 11/11 (~16h20 UTC) — inbox watch: 2 "aprovado" do Pedro
- **Listas de clientes** (aprovado): anexos do e-mail do Pedro (xlsx → csv no scratchpad); gatilhos publicados das duas
  contas relidos (nenhum reage a `client list import`/`active client`/`existing customer`/`past client`; só "Contact
  Created -> add owner" na Smart Chem). `pp_client_list_import.py --apply`: Bahama Blue 28 novos (27 ativos, 1 past),
  Smart Chem 63 novos, 0 erros. Conferido: tags certas, dono atribuído em todos, 0 conversas. Backups em
  `backup/<conta>/client-list-import-20261111-*.json`. Tarefa 86bd1ne90 fechada; Frank avisado no DM.
- **Aqua Clear — boas-vindas de reparo e obra** (aprovado; decisão 5 do guia): `scripts/pp_won_welcome.py` (novo, padrão
  da Corolla): no Won Stage, depois de "Mark won (Repairs / Installs)" e "Mark won (Construction)": e-mail (html no passo
  + snippet) → "Wait 2 minutes" (todo dia 08–18) → SMS (snippet). 4 snippets "Won Stage - Repair/Construction Welcome
  Email/SMS". Relido contra o backup (`backup/aqua-clear-pool-services-inc/won-stage-20261111-1623.json`): só os 6 passos
  novos + o `next` dos dois Mark won; status, re-entry, configurações e 3 gatilhos iguais. Frank avisado na tarefa
  86bc8yg7r. O "aprovado skip" (if/else existing customer em Missed Incoming Call / Missed New Lead) não veio → não feito.
## 11/11 — contas antigas no modelo (Pedro: "migra tudo, mantém o status") + Pool Duck fase 1 + inbox
- **Dashboard**: cópia de 10/11 levava os embeds da SwimReady (heat map/relatório local) → `pp_dashboard.py --replace-embeds`
  (copia a limpa, vira padrão, apaga a antiga; o padrão não pode ser apagado antes) em 33 contas + master; nas 22 que o Frank
  limpou, o widget GMB filtrava pelo place da SwimReady → place da conta (`PUT …/widget-preference`). Todas conferidas.
- **`pp_mirror --keep-status`** + `scripts/pp_fleet_migrate.py` (dump → pp_nps → mirror → pp_forms → pp_fix publicados →
  tags → skip_tag → review_fix → master_cleanup → review_gate → audit/ready/fleet_check). Regras: fluxo do snapshot que a conta
  tem = atualizado com o mesmo status; o que falta = criado draft (todos os do modelo menos 08 Paid Ads, IVR, "… Call - Tag" e
  Sequential Call Routing); a metade "Answered" do Incoming Call publicado sai publicada junto; versão própria da conta
  (IVR, passos/gatilhos sem cópia igual em 3+ contas ou no modelo — base congelada em `dump/_stock_baseline.json`) e texto de
  template do cliente ficam; sem dedupe e sem passada de status. `location_dirs` casa nome exato primeiro (Damon's ≠ Billing Only).
- Rodado em 34 contas (ABC + 32 dos lotes + Pool Smart OC): nenhum fluxo existente mudou de status (conferido pelos backups),
  0 publicados novos além do Answered. ERRO do pp_ready = fluxos novos em draft + dados do cliente vazios (combinado).
  **Específicos (não mexi)**: Damon's (Incoming Call, Website Form Fill), Clean Co (Website Form Fill), Ponchos (SMS Customer
  Reply), Ekahi (Review Request), Pooltexx (Website Form Fill draft), Wrigley's (Incoming Call, Website Form Fill), BluVantage
  (Incoming Call, Review Request, Website Form Fill), Clear Pool (Incoming Call, Review Request, Website Form Fill). Sem Google
  place → Review Request antigo mantido: Leisure, Premier 1 (2), Net Positive, Ponchos, Sparkling Clear, Reign, Wrigley's.
  Fora: Pool Palooza (sem Pool Leads), Golden View e o sub-account Pool Duck (estrutura própria).
- **Aqua Clear**: form do site novo do Frank não gerava card/aviso (Website Form Fill só ouvia o Landing Page) → `pp_forms`:
  Contact Form, Request a Quote, Lead Gen e Service Page no gatilho. Contato de teste do Frank apagado (backup).
- **Pool Duck fase 1** (`scripts/pd_v9_phase1.py`, `pp_mirror --model-dir … --new-only`): Odessa (334 contatos) e Lakewood Ranch
  (778; 356 clientes com `existing customer`): `pre-snapshot` em todos, pipeline "Pool Leads" ao lado (a deles intacta), 24 fluxos
  V9 em draft, campos/templates/custom values (do que a conta já tinha). 0 fluxo da Pool Duck mudou de status; 0 V9 publicado.
  Guardas nos gatilhos e publicação = fase 2, depois das respostas do Frank (e-mail no thread "Pool Duck Franchisee Accounts").
  Wesley Chapel por último.
- **Inbox (n8n)**: resposta do Pedro entra depois de 1 min (antes 5: o "aprovado" das 12h56 só seria visto às 14h); cadência
  igual (15 min no turno, 1 h depois); item noturno 21h "nightly-tasks" para a mesma rotina (revisão das tarefas). ClickUp sem
  API de lido → ✅ nas mensagens tratadas. Guia do CRM ao cliente: Pedro aprovou, pedido ao Frank. Resposta do guia = decisão
  do cliente (sem "[Aprovar]").
- **Dashboards — GA pela extensão do Chrome (Pedro, 11/11)**: 37 contas com GA. 26 com dados do próprio cliente, 4 com a
  propriedade certa sem tráfego, 2 com erro na propriedade (Big George's, Orange Tree), 5 sem propriedade sob val@ (Corolla,
  NorTex, Precision, Sparkling Clear, Wrigley's → trocar o login do widget para hello@; Sparkling e Wrigley's têm propriedade).
  A conta GA4 "Pool Profits" tem as propriedades de todos e a tela pré-seleciona a primeira (PoolTexx/Orange Tree) — sempre
  escolher a do cliente. Ads: Meta "Connection expired" em quase todas, Google Ads em 13; Next Level com Google Ads na conta
  9619764724 (aparece como da Clean Co; é a integração da conta, não o widget). Tudo que pede login → tarefa da Val
  86bd1zk8p (DM enviado).
- 11/11 2ª passada da extensão: NorTex e Wrigley's (hello@) e Sparkling Clear (success@) com dados do próprio cliente.
  Corolla e Precision sem saída: só val@ conectado, que só vê a propriedade "Pool Profits" (Precision ainda mostra o
  tráfego da agência, herdado da cópia). Southern e PoolReady SELA: 0 / "No data found" em todas as propriedades
  (provável tag GA ausente no site ou propriedade errada). Comentado na tarefa da Val 86bd1zk8p.

## 11/11 noite — inbox (Ed/Pool Duck, BluVantage no Group DM) + revisão da noite

- **Pool Duck — respostas do Ed** (8 perguntas): mover tudo para a Pool Leads (cards, fluxos de anúncio, conversões, Review
  Request), SMS de missed do V9, card de ligação só na principal, marcador no IVR da LWR, boas-vindas pela tag `new residential
  client`, avisos = mesmas pessoas (WC: dono responde 12/11), WC depois das 18h ET. Feito hoje:
  - "Free month" (varredura de templates + fluxos, Pool Profits e Pool Duck): templates limpos; o V9 não tem. Mas o fluxo
    antigo "In Communications" (snapshot pré-V9) → "Nurture Email Day 3" ("How Can You Earn Money With Us?") promete mês grátis
    por indicação em 33 contas + Pool Duck HQ. `scripts/pp_referral_offer_fix.py`: texto vira pedido de indicação sem oferta,
    assunto "Know Someone Who Needs a Pool Pro?" — aplicado nos 30 em draft (backup, status mantido). **Publicados (Pool Time,
    Reign, Sparkling Clear): a escrita foi bloqueada pelo classificador da sessão → falta rodar com OK do Pedro**
    (`--apply` com o nome da conta). Promoções próprias não mexidas: WC "Epperson Lead Bug Campaign", Blue Lagoon Reactivation
    (first month free), Pooly "Promo - 1 Free Month", ABC "First Service Free" (drafts). Correção mandada ao Ed.
  - WC "*Welcome NEW Residential Client Messaging": 2 publicados idênticos (mesmo e-mail/SMS; só o template_id do e-mail
    difere). A cópia `0974e427` → draft (backup `backup/poolduck-wesley-chapel/`); só 1 gatilho da tag ativo (conferido).
  - Odessa: custom value Owner First Name = "Matt" (backup). E-mail ao Matt pedindo os preços → [Aprovar] ao Pedro.
  - Fase 2 LWR/Odessa 12–13/11; ClickUp 86bcxzjfa em andamento (prazo 17/11).
- **BluVantage**: Ed perguntou no Group DM quem corrigiu o IVR. Conferido ao vivo: "Sequential Call Routing" v19 publicado,
  Ring Vanessa → Fred → Paul → caixa postal, gatilho ativo; nenhuma ligação de entrada depois do conserto. Respondido no DM;
  a resposta à Vanessa espera o teste do Pedro + aprovação.

## 12/11 (~12h UTC) — inbox (Frank: Puddle Jumper, Bonneville, Blissful, West Coast, Smart Chem) + rodada diária
- **West Coast**: link do Google do Frank (`share.google/…` → kgmid `/g/11x61hrn1n`) resolvido pelo Maps no Chromium →
  place `ChIJ6QYfYBK1OWoR6ld5NicqvpA` ("West Coast Chemical Company"). `google_review_link` = writereview?placeid=… (backup
  `backup/west-coast-pool-care/custom-values-20261112-1209.json`) → `pp_mirror --apply` → Review Request **published** com o
  place da conta; resto da sequência (forms/nps/fix/tags/skip/review_fix) sem mudança. `A2P Verification Number` estava vazio
  (ALTA 11 no audit) → telefone do negócio (323) 695-6810. Audit 0 ALTA, `pp_ready --place` 0 ERRO, fleet OK.
  `pp_new_account`: PUT `/locations` com `business` deu 422 "property business should not exist" → script tenta de novo só
  com `website`; brand website = go.westcoastpoolcare.com, campanha A2P preenchida. Falta o 1º número.
- **Capital**: "No Response Follow-up" tinha sumido da conta (apagado na tela) → recriado pelo `pp_mirror --apply` (0 contatos)
  + sequência; audit 0 ALTA, ready 0 ERRO. Número +19163124701 encaminhado e posto como A2P Verification Number.
- **WP Pools**: compra de número → 400 `NUMBERS_CARD_VERIFICATION_PENDING` (KYC ok, cartão não verificado) → DM ao Frank.
- Bonneville e Smart Chem: brand APPROVED / campanha VERIFIED (enviados pelo Frank na tela, não pela rodada → sem o aviso do
  item 8). Nenhum A2P enviado hoje. Contas novas: nenhuma (Puddle Jumper ainda sem o questionário 2.0).
- **Blissful**: go.blissfulwaterspoolcare.com aponta para sites.ludicrous.cloud mas está ligado à conta GHL antiga (location
  `qyxBYgM1Z79FCeL0IcaX`, outra agência) → recomendado ao Frank usar `info.` para o site A2P (CNAME no Wix).
- **Bonneville, lista de clientes**: Frank liberou importar. Anexo do chat do ClickUp não baixa (redirect para login; o
  conector do Basecamp também não entrega xlsx) → pedido ao Frank para anexar na tarefa 86bcz0y7b. A conta já tem número e
  A2P aprovado: reler gatilhos antes de importar.
- Smart Chem "Customize Pipeline & Opportunity Board" (86bd26424): Pool Leads padrão (13 etapas) conferido ao vivo, fechada.

## 12/11 (~14h20 UTC) — inbox (BluVantage: Vanessa + Frank)
- **BluVantage**: conferido ao vivo — "Sequential Call Routing" v19 publicado (Ring Vanessa → Fred → Paul → caixa postal).
  Ligação real 12/11 13:51 UTC (+19542838077 → linha principal) passou pelo passo "Ring Vanessa" (+14042249387) e foi
  atendida (132 s; o "telemarketer" do e-mail dela). Antes disso (11/11 tarde) as entradas não passavam pelo IVR.
  Vanessa agradeceu (sem resposta, thread lida); Frank perguntou da ligação de teste → respondido no Group DM com o
  horário da ligação real. TODO item 0 fechado.

## 12/11 (~15h UTC) — IVR: causa real da BluVantage + varredura de todas as linhas
- Causa real (não era o `pp_mirror`, que já deixava o Sequential Call Routing de fora): o `pp_fleet_migrate` roda
  `pp_master_cleanup --loc` em cada conta, e o `generic_ivr` dele tirava usuários dos passos Ring e a gravação da caixa postal
  de QUALQUER "Sequential Call Routing", publicado ou não, com usuários da própria conta ou não. A "trava no pp_mirror" citada
  no e-mail de 11/11 não tinha sido commitada (container perdido). Agora: `pp_master_cleanup --loc` pula fluxo publicado e
  passos com usuário da conta; `pp_mirror.own_version` pula passo `ivr_*` publicado ou com usuário/número. Testado em plano
  na BluVantage ("PUBLICADO: não mexo").
- `scripts/pp_call_check.py` (só leitura; as 2 agências, 71 contas): só a BluVantage foi atingida ao vivo, e já está certa (v19).
  Achados que não vieram de nós: IVR em draft com linha apontando para ele (Precision "Off Hours Voicemail" desde 18/06,
  Ponchos "IVR Automation" desde 09/09, Dream Pools "Inbound IVR Call Routing" desde 26/10 por outro usuário da agência,
  toll-free da Pool Profits); as ligações dessas linhas continuam entrando (completed/voicemail). Sunwave: os 2 IVRs editados
  11/11 22:56 pelo próprio Davey. Sobras da BluVantage PUBLICADAS desde a carga do snapshot (ago–out) em Passion, Southern e
  Pool Keepers (ouviam só os números da BluVantage, tocavam Fred/Paul) → **draft** com backup; linhas da BluVantage
  conferidas iguais depois.
- Teste do Pedro 14:19 UTC (+55…9401 → 404-334-2495): roteamento → Ring Vanessa, ela atendeu; card "Printed Marketing
  Materials". Contato e card apagados (backup). Frank respondido no Group DM; tarefa 86bd22q3e fechada.
- `pp_call_check` entrou no `pp_fleet_migrate` (para em ERRO) e na auditoria de quinta (item 3b).
- Reações no ClickUp (Pedro 12/11): não reagir em tudo; só de vez em quando, variando. Regra no TODO/inbox-watch; o prompt
  da rotina "GHL Tasks" (http_api, eu não edito) precisa ser colado pelo Pedro: `docs/routine-ghl-tasks-prompt.md`.
- 12/11 resposta do Pedro ao [Passo seu]: prompt novo da rotina colado; Refresh do snapshot feito (11/11 tarde e 12/11);
  tokens trocados; Call Recording Poolheads e form da LWR no Lead Ads feitos. Free month nos 3 publicados: Pedro não sabia
  que veio do Ed → perguntado ao Frank (DM) se algum dos 3 pediu a oferta antes de mudar ao vivo. Blue Lagoon $250: o Frank já
  respondeu a Caila no Basecamp em 06/11 → tarefa 86bcyu05g fechada. IVRs em draft: manter. Live tests 86bd1b3b5 enxugados
  (4 necessários + 4 opcionais; saíram YardSpring, BluVantage linha principal, NorTex).

## 12/11 — Inbox 20h UTC: NorTex ligação da Neena, spam da Passion, limpeza de pipeline (Reign)

- NorTex (Fareed "didn't get any call", Val pediu checagem): `pp_call_check --only NorTex` 0 ERRO (3 linhas no "IVR SPAM
  Detection", aperta 1 → toca o Fareed 10 s). Neena Kapoor 18:51 UTC na linha Meta: 0 s, no-answer, sem `ivr pressed 1` → o
  telefone não tocou. "Meta Ads Call - Weekly" rodou (SMS ao Fareed delivered, e-mail, tarefa); ela recebeu o SMS do V9 (número
  principal) + o text-back nativo (linha Meta). Fareed ligou de volta 19:15 UTC. Desde 31/10: 13 ligações de entrada, 1 contato
  apertou 1. Resposta ao cliente → [Aprovar] (opções: linha Meta direta, toque 20 s). Nada alterado.
- Passion Pool Care (spam no form): 8 submissões 13/10–12/11, 2 reais; 3 com telefone estrangeiro (+92/+91) vendendo
  serviço, 3 suspeitas. Proposta ao Frank (filtro +1 / palavras / telefone só EUA), esperando OK. Nada alterado.
- Reign (Frank): mover cards antigos sem disparar → proposta de tag `pipeline cleanup` com if/else no início dos fluxos de
  etapa (No Response, Quote Sent, No-Show, Won, Lost). Monto quando ele disser a data da call.

## 12/11 — Inbox 21h UTC
- NorTex: resposta aprovada postada ao Fareed (Basecamp "Paid Ads"); `enableMissedCallText` = false conferido ao vivo
  (desligado pelo Pedro). Frank avisado no DM.
- Corolla: LPs do Atif conferidas ao vivo (Weekly → form VdbZAHIJ2AmD6vD5RhyS, Repair → my5l2w6jE4yCGmPcgtoC, tel
  +12526002066); redirect_url dos 2 forms já aponta para os obrigados; fluxos Google Ads LP - Weekly/Repair e Won -> Google
  Ads publicados. Nada gravado. Falta envio real (Pedro).
- Pools of Perfection: `GET /snapshots` com o token Firebase → 401 (pede Authorization) → criação com snapshot pela tela.
