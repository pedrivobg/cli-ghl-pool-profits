# Pool Duck — landing pages de anúncio de Wesley Chapel → Lakewood Ranch (14/10)

Outra agência (GHL white-label `portal.poolduck.com`, company `yDnTmXSiDo0egbt77IY2`, 10 sub-contas).
Token Firebase próprio, fora do repo (`set -a; . <poolduck.env>; set +a` antes dos scripts; o
`.env` do repo continua sendo o da Pool Profits). Dumps em `dump/poolduck/` (`GHL_DUMP_DIR`).

- Origem: **Pool Duck Wesley Chapel** `uJr8H2qaQM5ffZxeYFqn`, pasta de funis "Ad Landing Pages".
- Destino: **Pool Duck Lakewood Ranch** `MosKIX4oux96vchwHZ5W` (941-588-2227).

## Feito

| O quê | Lakewood Ranch |
|---|---|
| Funil "Love Us Free, Hate Us Free" (Google) | `KVsiYlxVtBTUKYzRVkNt` → lakewoodranchflorida.poolduck.com/google-landing-page e /fb-thank-you-171844 |
| Funil "Love Us Free, Hate Us Free - FB" | `zfqO82ZBuj0LYBcAuel6` → /fb-promo e /fb-thank-you |
| Pasta de funis | "Ad Landing Pages" |
| Form "Google AdWords" | `L35gq3SnSDyoda4Kl9D4` (cópia da versão atual do WC; redireciona para /fb-thank-you-171844) |
| Form "Facebook Leads" | `331LWSK5w0JSbZFswx4q` (idem; redireciona para /fb-thank-you; sem o Pixel do WC) |
| Workflows (pasta "Ad Landing Pages") | Google AdWords / Facebook - Qualified Lead (Form Fill) **publicados**; (Call In) **draft sem gatilho** |
| Tags | `new lead`, `google adwords`, `fb leads`, `form fill`, `call in`, `lakewood ranch` |

Páginas: clonadas com o "clone to sub-account" do GHL (mesmo design/estrutura) e localizadas por
`scripts/pd_lwr_pages.py`: forms do LWR (inline e popup), telefone principal do LWR, "POOL DUCK
LAKEWOOD RANCH", "Pasco County" → Lakewood Ranch (a frase dos 15 anos virou "Over 15+ years of
pool service experience!" para não afirmar 15 anos em LWR), áreas atendidas, mapa (imagem nova,
link para o Google "Pool Duck of Lakewood Ranch"), "Centrally Located in Lakewood Ranch, FL", título
e descrição SEO. Reviews do WC (widget Trustindex do WC + depoimento Dennell M. + selos) ocultos.
Códigos de rastreamento (Google Ads/GTM/Meta Pixel) não foram copiados (decisão do cliente).

Workflows: espelho dos do WC com pipeline/etapa do LWR ("Leads --> Sales Pipeline" / Lead),
alerta SMS para **Kenton Dashiell (941-241-7595) e Pool Duck Service (941-549-3125 — no CRM é o
celular do Ricky)**, textos "Pool Duck Lakewood Ranch", tag `lakewood ranch` além de fonte +
meio. Sem os passos "Add to Google Ads" / "Meta Conversion API" até o LWR ter as contas.
SMS para o lead do FB: "Hi {{contact.first_name}}, this is Pool Duck in Lakewood Ranch…".

## Testes (14/10)

- Páginas ao vivo (navegador): sem nenhum texto de WC, forms do LWR carregando (inline e popup),
  título certo, sem Trustindex; mapa e áreas novos.
- Workflows rodados em 2 contatos de teste ("TEST - Pool Duck setup (… please ignore)", sem
  telefone): tags e card certos na pipeline do LWR; **alertas SMS entregues** (status delivered)
  para Kenton e para o 941-549-3125. Os 2 contatos/cards de teste ficaram para revisão do cliente.
- Envio do form: bloqueado por Cloudflare Turnstile para navegador automatizado (proteção legítima;
  não contornar) → teste manual (abaixo).
- Ligação: sem números de rastreamento no LWR ainda → teste depois (abaixo).

## Pendências (Pedro / cliente)

1. **Teste manual do form (1 min cada)**: abrir /google-landing-page e /fb-promo, enviar com dados
   de teste → deve cair no LWR com as tags, card em Lead e SMS para Kenton e 941-549-3125.
2. **Números de rastreamento**: o do Google Ads chegou (Val, 19/10): **+1 941-541-5942** ("Google Adwords",
   mesma configuração do número de Ads do WC: sem encaminhamento nem IVR). Feito 20/10: "Google AdWords -
   Qualified Lead (Call In)" com gatilho de ligação nesse número e **publicado** (`pd_lwr_workflows.py
   --only …`); páginas do funil Google (/google-landing-page e /fb-thank-you-171844) com o número novo
   (`pd_lwr_pages.py`, PAGE_PHONES; conferido ao vivo: 0 ocorrências do 588-2227). Falta: ligação de teste
   (Pedro) → conferir tags `google adwords`/`call in`/`lakewood ranch` + card e quem atende. Facebook: sem
   número ainda (páginas do FB continuam com a linha principal; "(Call In)" do FB em draft).
3. **Rastreamento de anúncios**: quando o cliente mandar Google Ads/GTM/Pixel do LWR, colocar nos
   funis e recolocar os passos de conversão nos workflows.
4. **Reviews**: criar o widget Trustindex do LWR (Google "Pool Duck of Lakewood Ranch") e reexibir a
   seção de reviews.
5. **Conferir com o cliente**: lista "Areas We Serve" (34202, 34211, 34212, 34240 / Lakewood Ranch /
   Bradenton / Sarasota / Manatee & Sarasota Counties) e horários (mantidos os do WC).
6. Apagar os 2 contatos/cards "TEST - Pool Duck setup" depois da revisão.
7. Fora do escopo, para avisar: os alertas de lead que o LWR já tinha ("… - Steve") não têm
   destinatário e atribuem a um usuário que não existe na conta. No WC, o popup do form está
   configurado com o form "Poolfessionals AdWords" de **outra empresa**; ao vivo aparece o form do
   WC, mas vale reselecionar o form do WC no popup para não arriscar.

## API do GHL (funis) — verificado ao vivo

- Clonar funil para outra sub-conta: `POST backend /funnels/funnel/clone-funnel-to-locations
  {funnelId, funnelName, locationIds}` (assíncrono, ~10 s). Não copia forms: **todo elemento de form
  vira `formId: "none"`**; não copia domínio nem códigos de rastreamento do funil.
- Corpo da página: JSON em `page.pageDataDownloadUrl` (`GET backend /funnels/page/{id}`).
  Salvar: `POST backend /funnels/builder/autosave/{pageId}` com `{funnelId, pageData, pageVersion,
  pageType: "live", manualSave: true, integrations, meta}`. **Sem `pageType: "live"` vira só
  rascunho** (Redis) e a página não muda. Live mantém o `pageVersion`.
- Domínio do funil: `POST backend /funnels/funnel/update-settings` (corpo do app de funis).
  Pastas: `/funnels/funnel/folder/create|list`, mover: `/funnels/funnel/move {folderId, funnelId,
  locationId, userId}`.
- Imagem na mídia da conta: `POST services /medias/files/ {name, contentType, parentId, altType,
  altId, size}` → PUT no `url` assinado → `POST services /medias/files/verify {altId, altType, id}`.
- Elementos (seção/linha/coluna/elemento) escondem com `extra.visibility.value.hideDesktop/hideMobile`.

# Campanha de review — clientes "turtle rock" (14/10)

Pedido do Ed (09/10): campanha de pedido de review para os clientes atuais (tag `turtle rock`, 309),
excluindo a lista da Connie (e-mail de 07/10, 38 nomes). `scripts/pd_lwr_reviews.py`.

- Exclusões: 37 contatos com a tag `exclude from reviews` (36 dos 38 nomes; lista e critério em
  `dump/poolduck/lwr-review-exclusions.json`). Grafias diferentes aceitas: Weinstraub → AARON
  WEINTRAUB, Clancy → WENDY CLANCEY, Brenda Callahan → BRENDAN CALLAHAN (único Callahan).
  "Ron McQuaid" não existe: excluídas Elizabeth McQuaid e "E MCQUAID" (mesma família — confirmar).
  Randal Briggs existe sem `turtle rock` (excluído mesmo assim). **Não estão na conta**: Carlos
  Martinez e Chris/Penny Steinbach.
- `public_review_link` = Google "Pool Duck of Lakewood Ranch" (writereview?placeid=ChIJd2NJ…).
- Workflow **"Review Request Campaign - Turtle Rock"** (publicado, pasta 7. Reviews & Referrals):
  gatilho tag `send review request` + filtro "Doesn't Have Tag: exclude from reviews" → SMS + e-mail
  → 4 dias → SMS lembrete. Sem incentivo e sem filtro por nota (contra a política do Google); o
  "Google Review Campaign" do snapshot (sorteio de US$150) **não** foi usado.
- Teste real: contato com o e-mail do Pedro recebeu o e-mail (status sent, de
  billing+lakewoodranch.poolduck.com@lc.poolduck.com); contato com a tag de exclusão não recebeu
  nada. Contatos de teste apagados.
- **Lançado 20/10 03:00 UTC** (Val: Connie aprovou; Ed: espaçar o envio): +3 exclusões (Barbara Beck, Larry &
  Judy Fogel, Tom Bachar; os McQuaid já estavam — "Ron" não existe como contato) → 40 excluídos, **271**
  marcados. Workflow agora: espera janela seg–sex 10:00–16:00 (America/New_York) → drip 20 a cada 20 min →
  SMS + e-mail → 4 dias (mesma janela) → drip → lembrete. Primeiro lote ter 20/10 10:00 ET, ~4,5 h no total.
- **Review gate (Pedro, 20/10 — padrão de todas as sub-contas)**: `scripts/pd_lwr_nps_gate.py`. NPS Score/Message
  criados, **NPS Form** da Pool Profits (`config/nps_form.json`) apontado para os campos da LWR
  (`YZxqfjtFpgH5QZ6iWREe`), `nps_survey_link` = https://api.leadconnectorhq.com/widget/form/YZxqfjtFpgH5QZ6iWREe.
  Campanha: janela → drip → SMS + e-mail pedindo a nota (link com e-mail/telefone) → espera a nota até 6 dias →
  4–5: tag `review gate - promoter` + SMS/e-mail com o Google; 0–3: tag `review gate - low score` + alerta SMS
  para Kenton e Pool Duck Service; sem resposta: janela → tag `review gate - no answer` + lembrete com o Google
  (igual ao timeout da Southern). Primeiro passo (onde estão os 271) mantido. Testado antes na LWR com 3 contatos
  (nota 5, nota 2, sem resposta → cada um no ramo certo; apagados).
- **21/10 (Val: "só 4 reviews no Google, cadê os 18?")**: os "5 estrelas" são notas da nossa pesquisa, não reviews.
  28 notas altas (26 × 5, 2 × 4), todos receberam o link do Google (27 por SMS + e-mail; Charlene Schmidt só e-mail,
  SMS bloqueado por ela desde fev.). Link certo (abre "Pool Duck of Lakewood Ranch", 5.0). E-mail: 11 abriram, 0
  cliques; clique de SMS não é rastreável. Google Business Profile não está ligado no GHL da LWR (reputação = 0
  reviews), então não dá para saber quem já postou. Oferecido: 1 lembrete aos 28 junto com o de segunda.
- **21/10 — lembrete aos promotores** (Val aprovou): `scripts/pd_lwr_promoter_reminder.py`. Workflow "Review Reminder -
  Promoters (Turtle Rock)" (7. Reviews & Referrals, publicado, re-entry off): tag `review reminder - promoters` (sem
  `exclude from reviews`) → espera a janela de **segunda 10:00–16:00 ET** → drip 20/20 min → SMS (texto de lembrete da
  campanha aprovado pelo cliente: "If you already left one, thank you so much!") + e-mail → tag `… sent`. **32**
  promotores marcados (eram 28 no recado à Val; 4 notas altas a mais desde então); 0 enviados até segunda. Check-in
  agendado para segunda 12:30 ET. GBP no GHL da LWR: Val/cliente vão conectar (precisa do login Google deles).
- (histórico) Não enviado até 19/10: aguardando o cliente aprovar os textos. Para disparar (274 clientes):
  `pd_lwr_reviews.py launch` (marca `send review request` em quem tem `turtle rock` e não está excluído).

# Google Ads: lead form + SMS (27/10, Val)

`scripts/pd_lwr_google_leads.py`. **"Google Ads SMS - New Lead"** publicado: Customer Replied, SMS, no número do Google
Ads +1 941-541-5942; spam/DND → nada; já mandou nas últimas 24 h → nada; cliente (`active residential client`, `turtle
rock`…) → alerta "EXISTING CUSTOMER", sem card; novo → tags `new lead`/`google adwords`/`google ads - sms`/`lakewood
ranch`, card em Lead ("Google Ads - SMS"), SMS ao Kenton + Pool Duck Service com o texto da mensagem.
**"Google Ads Lead Form - Qualified Lead"** criado em **draft sem gatilho**: o Google Ads **não está conectado** no GHL da
LWR (`googleAdwordsId` vazio). Mesma rota; novo → tags `google ads lead form`…, card ("Google Ads - Lead Form"), alerta e
o SMS ao lead do fluxo do Facebook. Depois de conectar (Settings → Integrations → Google Ads, com o Google que tem a conta
de anúncios) e mapear/ativar o form "Weekly pool service done right": rodar `apply` de novo (põe o gatilho e publica).
Testado nas cópias (6 casos). Falta: SMS real para 941-541-5942 e Send Data do form (me avisa antes: alerta ao Kenton).
- **27/10 tarde**: Val conectou pelo app "Google Lead Ads" (conta Pool Duck Lakewood Ranch, val@poolprofits.com, form
  "Weekly pool service done right", campanha Active, **Sync Disabled**). O app não preenche `googleAdwordsId`: gatilho
  criado sem filtro de conta e o workflow **publicado**. Falta: Play/Map Fields (Full Name, Email, Phone, Zip) + ativar a
  sincronização, e o Send Data no Google Ads (só a Val tem acesso).
