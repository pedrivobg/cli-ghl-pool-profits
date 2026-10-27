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
