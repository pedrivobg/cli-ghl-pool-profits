# Pool Brain / Skimmer → GHL: review quando o trabalho termina + Won → app de serviço (27–28/10)

Pedido do Derek (Clear Pool): disparar o pedido de review quando a OS (work order) passa de aberta para concluída no
Pool Brain, como faz o Applause (parceiro oficial do Pool Brain). Ed (28/10): sem conversar com o Pool Brain se der;
também Skimmer (concorrente; clientes nossos usam) e mandar o cliente Won direto para os dois apps.

## Pool Brain (spec oficial lida 28/10: prodapi.poolbrain.com/static/swaggerV2.json + Webhook Consumer Guide)
- **Webhooks** (Settings > API > Webhooks, toggle, URL HTTPS, HMAC `X-Webhook-Signature`): `customer.created`,
  `customer.status.updated`, `job.one_time.created`, `job.one_time.deleted`, `job.one_time.schedule.changed`,
  `technician.route.changed`, `alert.triggered`. **Nenhum "job concluído".** `alert.triggered` dispara só quando um job
  concluído tem alerta aberto (ex.: cloro baixo) — pega as visitas com problema, não todas; não serve para review.
  Payloads com ids/nomes, sem telefone/e-mail.
- **Open API REST** (header `ACCESS-KEY`, chave por empresa; "Master API Key" para várias empresas desde 08/2025):
  - `GET /v2/route_stops_job_list` (visitas semanais) e `GET /v2/one_time_job_list` (OS): `JobStatus`
    (`Completed`/`Not Completed`/`Scheduled`), `JobDate`, `CustomerId`, filtro por `fromLastModifiedDate/toLastModifiedDate`.
  - `GET /v2/customer_detail?customerId` → `Phone`, `Email`, `Contacts[]`; busca por `contactPhoneNumber`/`contactEmailAddress`.
  - `POST /v2/create_customer` {firstName, lastName, address, city, state, zipcode, contactNumber, email, waterBodyName,
    waterBodyType, waterBodyGallons, GateCode, accessNotes, serviceLevelId…} → cliente + propriedade + piscina.
  - Até 1000 registros por chamada.
- **Chave**: em 2024 era "sob pedido" (team@poolbrain.com ou chat do site). O dono da conta (Derek) olha primeiro em
  Settings > API (os webhooks já ficam lá); se não houver chave, ele pede pelo chat de suporte como cliente.
  Sem a chave da conta do cliente não há como testar nem acessar (é por empresa; não contornar).

## Skimmer (help.getskimmer.com release notes + devportal.getskimmer.com, 28/10)
- **API pública e webhooks só no plano Enterprise**: abas "API Keys" e "Webhooks" no próprio app (o cliente gera a chave).
  Header `skimmer-api-key`, 500 req/min. Release notes 2026: "new event integration partners can use to know the moment
  a work order is finished" (o review por OS concluída é possível no Skimmer Enterprise).
- Endpoints: `POST /Customers`, `GET /Customers/search` (por telefone/e-mail), service locations, bodies of water,
  `POST/PUT /WorkOrders`, `GET /WorkOrders/search`, `GET /Routes/GetAllRoutesForDay`.
- Abaixo do Enterprise: app privado do Zapier (chave própria pedida ao Skimmer): gatilho "novo cliente"; ações buscar
  cliente, criar OS — **sem criar cliente** e sem "OS concluída".
- Skimmer tem add-on próprio de Reviews (pedido de review automático) — conflito com o nosso se ligado.

## Desenho (quando houver a chave)
1. **Won → app**: workflow Won do GHL → Custom Webhook (o passo aceita headers) para um serviço pequeno nosso que busca
   pelo telefone/e-mail (não duplica) e cria cliente + propriedade (+ piscina) no Pool Brain/Skimmer.
2. **Review na conclusão**: Pool Brain — o serviço consulta `route_stops_job_list`/`one_time_job_list` a cada hora
   (modificados hoje, `Completed`), pega o telefone/e-mail e manda para o webhook de entrada do GHL (tag `job completed`)
   → Review Request com o NPS gate. Skimmer Enterprise — webhook de OS concluída, sem consulta.
3. Até lá: Review Request por tempo depois do Won (`scripts/cp_review_request.py`, draft).
