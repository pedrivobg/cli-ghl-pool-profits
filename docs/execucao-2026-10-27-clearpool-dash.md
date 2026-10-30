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
