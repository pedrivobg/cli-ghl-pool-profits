# Pool Duck — trazer o snapshot V9 para Lakewood Ranch, Odessa e Wesley Chapel (plano, 04/11)

Pedido do Frank (e-mail 03/11): levar o snapshot atual da Pool Profits (V9; master "Snapshot Pool Profits"
`Kvdj7o189zlS3caaCNuX`, estado-alvo em `docs/modelo-southern.md`) para 3 franquias da **agência Pool Duck**:
Lakewood Ranch (LWR) `MosKIX4oux96vchwHZ5W`, Odessa (ODE) `w3foSSaVaQw2ngI3beq0`, Wesley Chapel (WC)
`uJr8H2qaQM5ffZxeYFqn`. Condições dele: ver antes se cada conta tem leads/contatos ativos; **nada pode disparar
para contatos que já existem** (boas-vindas, SMS, e-mail, aviso); na WC (clientes e leads ativos) contatos e cards
continuam andando na pipeline sem disparar as automações novas; preservar tudo; desligar o que for preciso durante a
importação e religar depois.

Este documento é **só leitura/plano**: nada foi alterado em nenhuma conta, ninguém foi contatado.
Fonte: dumps de 04/11 (`pp_dump.py` com `GHL_DUMP_DIR=dump/poolduck` + contatos, cards e números lidos pela API,
salvos em `dump/poolduck/<slug>/contacts.json|opportunities.json|numbers.json` — dado de cliente, fora do git) e
dump do master (`dump/snapshot-pool-profits/`). Só contagens aqui.

---

## 1. Inventário atual das 3 contas

Classificação dos contatos (heurística): **cliente** = veio do QuickBooks (`source: quickbooks`/`qboId`) ou tem tag
de cliente (`turtle rock`, `active residential client`…); **lead** = tem card ou tag de lead (`new lead`, `call in`,
`form fill`, `google adwords`, `fb leads`, `gbp`, `google lsa`, `sms`…); **só ligou** = só as tags do caller lookup
(`couldn't find caller name`, `name via lookup`, `spam likely`); **lista de campanha** = `estancia 7x7`, `epperson`,
`theleadbug`.

### Resumo

| | Lakewood Ranch | Odessa | Wesley Chapel |
|---|---|---|---|
| Contatos | **771** | **328** | **2.621** |
| Criados últimos 30 / 90 dias | 27 / 111 | 10 / 97 | **198 / 500** |
| Atividade nos últimos 30 dias (`lastActivity`) | 306 | 13 | 304 |
| Clientes / leads / só ligou / campanha / sem sinal | 355 / 5 / 378 / 0 / 33 | 0 / 1 / 310 / 0 / 17 | **1.237** / 300 / 552 / 289 / 243 |
| Clientes que também têm sinal de lead | 5 | 0 | 102 |
| Sem nenhuma tag | 53 | 17 | 1.307 |
| Com telefone / e-mail | 751 / 338 | 326 / 5 | 2.171 / 1.195 |
| Cards (todos abertos, etapa **Lead**) | 4 | 0 | **97** (45 criados/movidos nos últimos 30 dias) |
| Workflows (publicados / draft) | 75 (18 / 57) | 62 (7 / 55) | 136 (25 / 111) |
| Pipelines | 1 | 1 | 1 |
| Calendários (ativos) | 14 (6) | 8 (2) | 15 (5) |
| Forms | 15 | 11 | 22 (11 nomes em dobro) |
| Campos customizados | 55 | 53 | 62 |
| Custom values (vazios) | 25 (7) | 32 (8) | 24 (9) |
| Usuários | 7 (todos admin) | 2 (admin) | 5 (4 admin, 1 user) |
| Templates (snippets) / tags da conta | 13 / 67 | 5 / 38 | 8 / 63 |
| Fuso | America/New_York | America/New_York | America/New_York |
| Missed-call text **nativo** | **ligado** | **ligado** | **ligado** (texto próprio, assinado por uma pessoa da equipe) |
| Google Place / conta Google Ads na location | sim / não (app Lead Ads) | sim / não | sim / sim |

**Conclusão do item 1 do Frank:** as três têm contatos; LWR e WC têm clientes de verdade (QuickBooks) e leads
recentes; a WC é a mais viva (≈200 contatos novos/mês, 97 cards abertos, 4 linhas). Odessa é quase só gente que ligou
(sem clientes, sem cards). Nenhum contato está parado em workflow agora (`activeWorkflows` vazio nas três).

### Pipeline (igual nas três — vem do snapshot da Pool Duck)

`Leads --> Sales Pipeline`: Lead → Engaged Lead → Pool Quote Call Booked → Pool Quote Call Cancelled / No Show →
Didn't Sign Up → Customer → Bad Fit.
Cards: LWR 4 e WC 97, **todos em "Lead", status open**. Origem dos 97 da WC: Google Ads ligação 34, Facebook form 25,
Google LSA 24, Google Ads form 12, outros 2.

### Telefones

| Conta | Linhas | Roteamento |
|---|---|---|
| LWR | 2: principal (padrão) e "Google Adwords" | principal → **IVR publicado** ("Active - Phone Tree IVR", sem tag `missed call`); Google Ads sem IVR/encaminhamento |
| ODE | 1: principal | **encaminhamento** para um número externo |
| WC | 4: "Pool Duck" (padrão), "AdWords", "LSA", "Facebook Leads" | sem IVR e sem encaminhamento no número (tocam no app) |

### Workflows publicados (gatilho → o que fazem)

**Comuns às três (vieram do snapshot da Pool Duck):**
- `*Welcome NEW Residential Client Messaging` — tag `new residential client` → e-mail + SMS de boas-vindas.
  **Na WC está publicado em DOBRO** (duas cópias com o mesmo gatilho → cliente novo recebe 2 e-mails e 2 SMS hoje).
- `New Pool Quote Request Form Submitted - Residential - <responsável>` e `Pool Quote Request Form Submitted - <responsável>`
  — form do site (+ filtro do campo "Request for Pool Service") → avisos internos (LWR/ODE 1 responsável; WC 2).
- `Send Pool Service Quote Form Link` — tag `sent pool service quote form link` → SMS + e-mail (WC em dobro).
- `Webchat Submission Notification - <responsável>` e `Message via Chat Widget notification` — Customer Replied
  tipo webchat → avisos internos (WC: 4 workflows no mesmo gatilho, 2 em dobro).
- `Credit Card / ACH update request workflow` — tag `credit card declined` → SMS + e-mail (WC em dobro).

**Só LWR (nossos, out–nov):** IVR da linha principal; Google Ads: form, ligação, SMS, lead form e comercial (cards na
pipeline da LWR, alerta ao responsável, filtros de spam/cliente/24 h); Facebook form; `Missing Email - Send SMS`
(tag); `Send invite to Customer Portal Email` (tag); **campanha de review em andamento**: `Review Request Campaign -
Turtle Rock` (tag `send review request` + "Doesn't Have Tag: exclude from reviews"; 271 marcados, 235 no ramo "no
answer") e `Review Reminder - Promoters (Turtle Rock)` (32 marcados).

**Só WC:** `TAG Orchestrator` (Customer Replied/ligação por linha + forms de anúncio → tags de origem; não cria card);
`LSA Call Flow` (ligação na LSA → tags + card); `Google AdWords - Qualified Lead (Call In / Form FIll / Lead Form)` e
`Facebook - Qualified Lead (Call In / Form FIll)` (card em Lead + conversão Google/Meta, aviso interno, SMS ao lead do
FB); `Google AdWords - Converted Lead (Form Fill)` (**etapa Customer** → conversão no Google Ads);
`7 x 7 - Estancia Drip Template` (tag `estancia 7x7` → 7 e-mails); `Epperson Lead Bug Campaign` (card criado com tag
`epperson` → 3 e-mails); `Residential Property & Media Release Form Signed` (documento assinado).

**Drafts (não mexer):** a família da Pool Duck/ZappyChat — 1.01–4.03 (follow-up, lembretes, stale lead, reativação,
**3.07 Inbound Missed Call**), 6.01–6.04 (review/referral), 7.00–7.12 (nurture mensal), **8.01 Birthday e 8.02–8.06
feriados (por data)**, AI.01–AI.10, Google Review Campaign (sorteio). Na WC todos em dobro (snapshot carregado 2×).

### Custom values / campos (nomes da Pool Duck)

Custom values: Known As Business Name, From Name/Email, CRM Phone Number, Click to Call Company Phone Number, Domain,
A2P Privacy/Terms URL, Public Review Link, Logo Image URL/Business Logo, Pool Service Area, Pool Brain Customer Portal
Link, cores, ZC - … (ZappyChat). Odessa tem também A2P - … e **Legal Business Name (preenchido)**; LWR tem **NPS Survey
Link** (nosso). Campos: 53–62 da Pool Duck (billing, call notes, nurture, feriados, UTM na WC); LWR tem **NPS Score /
NPS Message** (nossos, review gate).

---

## 2. Inventário do V9 (master "Snapshot Pool Profits", dump 04/11)

- **Pipeline "Pool Leads"** (13 etapas): 🆕 New Lead → No Response - Follow Up → 💬 In Communication → 📅 Scheduled →
  💰 Quote Sent → No Show → 🏆 Won - Weekly Pool Service → 🏆 Won - One Time Repair or Install → 🏆 Won - Pool
  Construction or Remodeling → 🔄 Recurring Customer → ❄ Not Qualified Stage → ❌ Lost → 🚫 Spam.
- **Campos (6):** Client Type, NPS Message, NPS Score, Rate, Rate Type, Reactivation Reason.
- **Custom values (21):** A2P Domain, A2P Verification Number, Business Address/Email/Phone, Chemical Only Price,
  Client Domain Name, Friendly Business Name, Google Review Link, Green to Clean Price, Legal Business Name, Logo URL,
  NPS Survey Link (aponta para o form NPS **no domínio da Pool Profits**), One-Time Clean Price, Owner First Name,
  Pool Service Appointment/Estimate Link, Privacy Policy, Service Area, Terms of Use, Weekly Service Price. No master
  estão com valores de exemplo ("We Clean Pool", telefone fictício, owner = Pedro).
- **Tags (34):** adwords, adwords call in, adwords won, appointment booked, dnd, do not remarket, **existing customer**,
  filter cleaned, follow-up, form submitted, good lead, green pool, high priority, in communication, inbound call,
  lost lead, **missed call**, new form fill, new lead, no-show, one-time customer, pool service lead, quote sent,
  **reactivation**, recurring customer, review received, review requested, service completed, spam,
  upsell opportunity, won, won construction, won repairs and installs, won weekly.
- Também: 7 forms (NPS, Landing Page, Service Page, Client Onboarding, Lead Gen, Post-Visit, Appointment Booking),
  2 calendários, 34 templates, **11 funis/sites** (incl. "… - Simple Pool Care"), 0 usuários.
- Pendente do nosso lado: **Refresh do snapshot V9** (TODO 13) — o master tem as correções de 22–23/10 que o snapshot
  compartilhável talvez ainda não tenha.

### Workflows (28: 17 publicados, 11 draft no master)

| Pasta | Workflow | Status | Gatilho | Mensagens |
|---|---|---|---|---|
| 01 | Answered Incoming Call To Pipeline | pub | `call_status` entrada, completed (**qualquer linha**) | tag + card + tarefa |
| 01 | Missed Incoming Call To Pipeline | pub | `call_status` entrada busy/canceled/voicemail/no-answer (qualquer linha) | tag `missed call` + card + tarefa |
| 01 | Missed New Lead - Initial SMS Follow-up | pub | tag `missed call` | **2 SMS ao contato** |
| 01 | SMS Customer Reply to pipeline | pub | Customer Replied SMS + tem tag `reactivation` | card + 2 avisos internos |
| 01 | Website Form Fill To Pipeline | pub | form (3 forms do snapshot) | card + aviso + tarefa |
| 02 | No Response Follow-up | pub | tag `follow-up` **ou** etapa No Response | **3 SMS** → Lost |
| 02 | No-Show Follow-up | pub | tag `no-show` **ou** etapa No Show | **2 SMS** |
| 02 | Quote Sent Follow-up | pub | etapa Quote Sent | **2 SMS** |
| 03 | Appointment Confirmation/Reminders | draft | agendamento confirmado (calendário V9) | 3 SMS + aviso |
| 03 | Post-Appointment Follow-up | draft | etapa Won Weekly (sem `existing customer`) | SMS |
| 04 | In Communication Stage | draft | etapa In Communication | 3 e-mails |
| 04 | Lost Stage | pub | etapa Lost | **2 e-mails** |
| 04 | Recurring Customer Stage | pub | etapa Recurring | só tag/campo |
| 04 | Spam Contact | pub | etapa Spam | tag + **DND** |
| 04 | Won Stage | pub | 3 etapas Won, filtro "Doesn't Have Tag: existing customer" | **e-mail + SMS de boas-vindas** |
| 05 | Review Request | draft | 3 etapas Won (com filtro `existing customer`) | SMS/NPS/link do Google + aviso |
| 05 | Review Response - Negative / Positive | pub | review nova no Google (≤3 / ≥4) | **SMS ao autor** (+ tarefa) |
| 06 | Filter Clean Reminder / Monthly Service Reminder / Upsell Opportunity | draft | tag / etapa Recurring / tag | e-mail/SMS |
| 07 | Reactivation Campaign - Email / SMS | pub | tag `reactivation` | **3 e-mails / 3 SMS** |
| 08 | AdWords Call In / AdWords Form / Adword Call - Conversion | draft | — / form / Won | conversão + SMS |
| 09 | Contact Created -> add owner | pub | contato criado | atribui usuário |
| 09 | Sequential Call Routing | draft | — (IVR) | — |

---

## 3. Conflitos

### 3.1 Mesmo nome (o import sobrescreveria ou duplicaria)

| Conta | Workflows | Pipelines | Campos | Custom values | Forms | Tags |
|---|---|---|---|---|---|---|
| LWR | nenhum | nenhum | **NPS Score, NPS Message** | **NPS Survey Link** | **NPS Form** | new lead, review received |
| ODE | nenhum | nenhum | nenhum | **Legal Business Name** (preenchido, usado no A2P) | nenhum | review received |
| WC | nenhum | nenhum | nenhum | nenhum | nenhum | new lead, quote sent, reactivation, review received, won |

- LWR: os 3 itens NPS são os do review gate que está no ar (a espera lê o campo pelo id). **Sobrescrever ou duplicar
  quebra a campanha.** O V9 tem que usar os da LWR.
- ODE: sobrescrever `Legal Business Name` com "We Clean Pool LLC" estraga o A2P/site.
- Tags com o mesmo nome se fundem (sem risco); `reactivation` já existe na WC (0 contatos com ela hoje).
- **Duplicados por significado** (nomes diferentes, mesma coisa): Friendly Business Name × Known As Business Name;
  Business Phone × CRM Phone Number/Click to Call; Business Email × From Email; Google Review Link × Public Review Link;
  Logo URL × Logo Image URL; Service Area × Pool Service Area; Client Domain Name/A2P Domain × Domain; Privacy Policy /
  Terms of Use × A2P Privacy/Terms URL. Os V9 chegam vazios (Pool Keepers, 21/10) ou com o exemplo do master → **toda
  mensagem do V9 sairia com nome/telefone em branco ou "We Clean Pool"** até preencher (copiar dos da Pool Duck).
- Pipelines: nomes diferentes → o V9 cria uma **segunda pipeline** ("Pool Leads") ao lado da "Leads --> Sales Pipeline".

### 3.2 Gatilhos do V9 que podem pegar contatos que JÁ existem

| Gatilho V9 | Como pega contato antigo | LWR | ODE | WC |
|---|---|---|---|---|
| `call_status` (Answered/Missed Incoming Call) | **qualquer ligação de entrada, de qualquer linha, de qualquer contato** — cliente ligando vira card "New Lead" + tag `new lead` + tarefa; perdida → tag `missed call` → **2 SMS de "sorry we missed your call / we'd love to help keep your pool clean" para o cliente** | ALTO: IVR na principal → toda ligação vira "completed" → Answered dispara para todas; Missed nunca dispara na principal | MÉDIO (encaminhamento: Missed funciona) | **ALTO**: 1.237 clientes, 4 linhas; nas linhas de anúncio já existe fluxo próprio que cria card → **2 cards por ligação** (um em cada pipeline) |
| tag `missed call` (Missed New Lead SMS) | qualquer um que receba a tag (Missed, IVR, alguém da equipe) | — | — | — |
| tag `follow-up`, `no-show`, `reactivation`, `recurring customer`, `upsell opportunity` | se alguém da equipe aplicar a tag (em massa, inclusive) | baixo hoje (0 contatos com elas) | baixo | `reactivation` já existe na conta → aplicar em massa dispara 3 SMS + 3 e-mails |
| `customer_reply` (SMS Customer Reply) | só quem tem `reactivation` | baixo | baixo | baixo |
| `pipeline_stage_updated` (No Response, Quote Sent, No-Show, Lost, Spam, Recurring, Won, Review Request) | só cards na **"Pool Leads"**; hoje nenhum card está lá. Se a equipe mover cards antigos para lá (ou se migrarmos), cada etapa dispara: SMS de follow-up, e-mail de Lost, **DND no Spam**, boas-vindas no Won (este tem o filtro `existing customer`, os outros não) | baixo enquanto a pipeline nova estiver vazia | idem | **ALTO se os 97 cards forem movidos** |
| `reputation_review_received` (Review Response) | **qualquer review nova** no Google, de qualquer pessoa → SMS ao autor; o Positive promete "every referral earns you a free month of service" | ALTO quando o GBP for ligado: a campanha de review da LWR está gerando reviews dos clientes | baixo | médio (GBP/Place na conta) |
| `contact_created` (add owner) | não é retroativo; mas **todo contato novo vindo do QuickBooks** (cliente) entra; atribuir dono gera aviso de atribuição ao usuário | baixo | baixo | médio (sync do QuickBooks ativo) |
| `form_submission` (Website Form Fill) | só os forms do V9 (que não estão em página nenhuma) — se o `pp_forms` ligar os forms da conta, entra em dobro com os alertas que já existem | — | — | — |
| `appointment` (draft) | só o calendário do V9 | — | — | — |
| Aniversário / data | o V9 **não tem**; os da Pool Duck (8.01 Birthday, feriados) estão em draft e assim ficam | — | — | — |

### 3.3 Fluxos da conta que dobrariam com o V9

- **Dois missed-call texts**: nativo ligado nas 3 + "Missed New Lead - Initial SMS". Hoje o nativo já manda SMS para
  **qualquer** ligação perdida, inclusive de cliente (WC com texto próprio).
- **Dois cards / dois alertas por lead de anúncio (WC, LWR)**: as linhas de Google/FB/LSA já criam card + avisam; o
  Answered/Missed do V9 escuta todas as linhas.
- **Dois alertas de form**: forms do site já avisam os responsáveis; não rodar `pp_forms` aqui (o Website Form Fill
  ficaria sem forms ou só com forms novos).
- **Duas boas-vindas**: `*Welcome NEW Residential Client` (tag `new residential client`; WC em dobro) × Won Stage do V9.
- **Dois pedidos de review (LWR)**: campanha Turtle Rock + NPS gate no ar × Review Request/Review Response do V9.
- **Duas conversões no Google Ads (WC)**: `Google AdWords - Converted Lead` (etapa Customer) × `Adword Call -
  Conversion` do V9 (draft; manter draft).
- **IVR**: o "Sequential Call Routing" do V9 não serve (LWR tem IVR próprio; WC/ODE outro roteamento) → fica draft.

### 3.4 Cards da WC × pipeline do V9

Os 97 cards estão em `Leads --> Sales Pipeline / Lead`. Os workflows da WC que criam card (LSA, Google ligação/form, FB
ligação/form) apontam para essa pipeline e a conversão do Google Ads dispara na etapa **Customer** dela. O V9 aponta para
"Pool Leads". Equivalência de etapas, se um dia migrar:

| Leads --> Sales Pipeline | Pool Leads (V9) |
|---|---|
| Lead | 🆕 New Lead |
| Engaged Lead | 💬 In Communication |
| Pool Quote Call Booked | 📅 Scheduled |
| Pool Quote Call Cancelled / No Show | No Show (**dispara No-Show Follow-up**) |
| Didn't Sign Up | ❌ Lost (**dispara Lost Stage**) |
| Customer | 🏆 Won - Weekly Pool Service (**dispara Won Stage** sem `existing customer`) |
| Bad Fit | ❄ Not Qualified Stage |
| — | No Response, Quote Sent, Won One Time/Construction, Recurring, Spam (sem equivalente) |

Hoje todos os 97 estão em "Lead" → mover para New Lead não dispara nada do V9 (não há gatilho em New Lead).

---

## 4. Como levar entre agências

### (a) Snapshot compartilhado (UI)

1. Pedro (Pool Profits): **Refresh** do "Snapshot Pool Profits v9" → Snapshots → ⋮ → Share → link para outra agência.
2. Admin da agência Pool Duck abre o link logado em portal.poolduck.com → Import → o V9 aparece nos snapshots da Pool
   Duck (serve para franquias futuras também).
3. Carregar na sub-conta existente (Snapshots → ⋮ → push/load em sub-conta existente; o nome do botão varia — conferir
   na tela). Seleção:
   - **Marcar**: Workflows, Pipelines, Custom Fields, Custom Values, Tags, Templates/Snippets, Forms (o NPS Form só onde
     não existe).
   - **Desmarcar**: Funnels/Websites (11 sites da Pool Profits/Simple Pool Care), Calendários (o baseline não usa),
     Trigger links/Media se aparecerem, qualquer coisa de contatos.
   - Conflito de nome: **nunca "Overwrite"** — sempre manter o existente (LWR: NPS Score/Message, NPS Survey Link,
     NPS Form; ODE: Legal Business Name).
4. **Rodar o vigia** `pp_guard_new_workflows.py --loc <id>` (token Pool Duck) antes do clique: na Pool Keepers
   (BurchTech, 21/10) 18 de 28 workflows chegaram **publicados** e o vigia pôs em draft em 12–34 s (nenhuma mensagem
   saiu). Ainda assim é uma janela de ~30 s com gatilhos ativos.
- Prós: ids internos (funil, campo, forms, templates) já vêm convertidos; a Pool Duck fica com o V9 para as próximas
  franquias. Contras: janela de segundos publicada; precisa de admin da agência Pool Duck na UI; sem controle fino do que
  entra (pipeline/campos/custom values entram todos).

### (b) Espelho pela API com os dois tokens (como `ph_migrate_old.py`)

Lê o master com o token Pool Profits e escreve na conta Pool Duck com o token Pool Duck (`new_agency()`/dois
`TokenManager`). Script novo `scripts/pd_v9_port.py` (plan/apply, por conta), juntando o que já existe:
- cria **Pool Leads** (`PUT/POST` pipeline), os 6 campos (os que faltam), os custom values que faltam **já preenchidos
  com os da Pool Duck** (tabela da seção 5), as tags (`pp_tags_missing`), os 34 templates (`snippets` do
  ph_migrate_old), o NPS Form só onde não existe;
- cria os 28 workflows **sempre como draft** (`POST backend /workflow/{loc}` + gatilhos; draft = gatilho inativo),
  trocando todo id do master (pipeline/etapas, templates, forms, campos, usuários, workflows do `remove_from_workflow`,
  ids de gatilho do if/else — `pp_trigger_ref_fix`) pelos da conta;
- já grava os guardas (seção 5) e as decisões por conta (linhas, nativo, boas-vindas);
- backup de tudo que tocar em `backup/poolduck-<slug>/`, re-leitura com espera (leituras defasadas).
- Prós: **zero janela publicada**, nada sobrescrito, entra só o que se escolhe, reutiliza o que a LWR já tem.
  Contras: script novo (≈1 turno para escrever + teste); sites/funis não vêm (não precisamos); a Pool Duck não fica com
  o V9 como snapshot dela.

### Recomendação

| Conta | Caminho | Por quê |
|---|---|---|
| **Odessa** | **(a)** snapshot + vigia, à noite (ET) | conta quieta (13 contatos ativos/30 dias, 0 cards, sem clientes, sem colisão além do Legal Business Name); serve de piloto do link e deixa o V9 dentro da agência Pool Duck |
| **Lakewood Ranch** | **(b)** API | já tem os nossos fluxos, o review gate no ar e as colisões NPS; precisa reaproveitar, não importar por cima |
| **Wesley Chapel** | **(b)** API | conta mais viva (clientes do QuickBooks, 97 cards, 4 linhas, ~7 contatos novos/dia): nenhuma janela publicada é aceitável para o "nada pode disparar" |

Se o Frank preferir a UI em todas: (a) também funciona na LWR/WC, desde que à noite, com o vigia, sem overwrite, e os
passos de guarda abaixo feitos **antes** de publicar qualquer coisa.

---

## 5. Plano de migração seguro

### Regras para as três

- **Tudo do V9 entra em draft.** Publicação uma a uma, depois de testada, na ordem da seção 5.4.
- **Tag de guarda em todos os contatos existentes**: `pre-snapshot` em 100% dos contatos no momento da migração
  (LWR 771, ODE 328, WC 2.621) + `existing customer` (tag do V9) nos clientes (LWR 355, WC 1.237). Conferido: nenhum
  workflow publicado das contas tem gatilho de tag sem filtro, nem escuta essas duas → aplicar não dispara nada
  (`POST /contacts/{id}/tags`, nunca o upsert com tags).
- **Todo gatilho do V9 que pode pegar contato antigo ganha o guarda**:
  - gatilhos de etapa/tag/Customer Replied: filtro "Doesn't Have Tag: `pre-snapshot`" (formato da UI, testado em
    `pipeline_stage_updated`), além do `existing customer` que o Won/Review já têm;
  - ligação, review recebida, contato criado: if/else no topo `contact_detail / tags / index-of-false` (`pre-snapshot`,
    `existing customer`, `spam`, `dnd`) envolvendo a cadeia (padrão testado do `pp_lead_alerts`);
  - Missed New Lead SMS: if/else no topo também (a tag `missed call` pode vir de outro lugar).
  Para pôr um lead antigo de propósito no fluxo novo: tirar a `pre-snapshot` dele antes de mover o card.
- **Usuários** nos avisos/tarefas/dono: só usuários da própria conta (o master não tem nenhum) — quem, o Frank diz.
- **Custom values V9 preenchidos** a partir dos da conta: Friendly Business Name ← Known As Business Name; Business
  Phone ← CRM Phone Number; Business Email ← From Email; Google Review Link ← Public Review Link (ou
  `writereview?placeid=` do Place da conta); Logo URL ← Logo Image URL; Service Area ← Pool Service Area; Client
  Domain Name/A2P Domain ← Domain; Privacy/Terms ← A2P URLs; Legal Business Name/Business Address ← Business Profile;
  A2P Verification Number ← número GHL da conta; NPS Survey Link ← widget do NPS Form **da conta**; Owner First Name e
  preços ← Frank; links de calendário vazios (`pp_fix --drop-booking`).
- **Não mexer**: fluxos e drafts da Pool Duck, a pipeline "Leads --> Sales Pipeline", forms, IVR, números, campanha de
  review da LWR. Os achados (WC com workflows publicados em dobro) vão para o Frank como aviso, sem correção sem pedido.
- **Testes**: só em cópias "ZZ TEST" dos workflows (avisos desviados para o Pedro) com contatos "ZZ TEST" sem telefone
  de cliente; nunca `pp_e2e.py` em conta de cliente; tudo de teste apagado no fim (contato, card, tarefa, workflow).
- **Fim**: `pp_dump` (GHL_DUMP_DIR) → `pp_audit` / `pp_ready` (com as exceções Pool Duck) → monitorar 48 h as
  mensagens de saída para contatos com `pre-snapshot` (meta: zero).

### 5.1 Wesley Chapel (detalhado)

**Antes (dia −1)**
1. Combinar janela com o Frank (fora do horário comercial ET) e pedir à equipe da WC para não mexer em
   tags/cards em massa nesse dia.
2. Backup completo: `pp_dump` + contatos/cards/números/location → `backup/poolduck-wesley-chapel/pre-v9-<data>/`
   (inclui os 25 publicados com gatilhos, a pipeline e os custom values).
3. Plano do script (`pd_v9_port.py --loc uJr8… plan`): lista de criações, mapa de ids, diff dos guardas. Revisar.

**Dia da migração**
4. Criar as tags `pre-snapshot` e `existing customer`; marcar os 2.621 contatos com `pre-snapshot` e os 1.237 clientes
   do QuickBooks com `existing customer` (só adiciona tag; nada dispara). Recontar.
5. `apply` (tudo draft): pipeline Pool Leads, 6 campos, custom values preenchidos, tags V9, 34 templates, NPS Form,
   28 workflows com os guardas e:
   - **Answered/Missed Incoming Call**: gatilho só na linha principal "Pool Duck" (`inbound_number`); as linhas
     AdWords/LSA/Facebook continuam só com os fluxos da WC (um card por ligação). Guarda de cliente/pre-snapshot no topo.
   - **Website Form Fill**: sem forms da conta (os forms do site já têm aviso e card) — fica draft.
   - **Won Stage**: e-mail de boas-vindas só se o Frank escolher o do V9; senão o `*Welcome NEW Residential Client`
     continua sendo o único.
   - **Review Request / Review Response / Reactivation / 08 Paid Ads / 03 / 06 / Sequential Call Routing**: draft.
6. Conferir pelo dump: 0 workflows V9 publicados, 0 gatilhos ativos, 25 publicados da WC iguais ao backup.

**Cards existentes — recomendação: fase 1 sem mover**
7. Os 97 cards ficam na "Leads --> Sales Pipeline" e a equipe continua andando com eles como hoje (nenhum workflow do V9
   escuta essa pipeline; a conversão do Google Ads em Customer continua).
   Leads novos que entram pela linha principal vão para "Pool Leads"; os de anúncio continuam na pipeline antiga.
8. Fase 2 (só com OK do Frank/Ed, outro dia): mover os 97 para Pool Leads / 🆕 New Lead (PUT do card com backup; New Lead
   não tem gatilho; os contatos têm `pre-snapshot`), **e** trocar nos 5 fluxos de anúncio da WC o "create opportunity"
   para Pool Leads/New Lead e o gatilho da conversão do Google Ads de Customer para as 3 etapas Won — sem isso os leads de
   anúncio voltam para a pipeline antiga e as conversões param. Riscos: mudar a lógica dos fluxos da WC (pedido
   explícito necessário); depois disso, mover um card antigo para Quote Sent/No Show/Lost **não** manda nada (guarda),
   o que precisa ser explicado à equipe.

**Testes (em cópias, antes de publicar cada grupo)**
9. Contato ZZ TEST **com** `pre-snapshot` passado por cada etapa da Pool Leads e por cada tag do V9 → nenhuma execução
   com mensagem. Sem a tag → segue o V9 (SMS para o número de teste do Pedro). Contato com `existing customer` → Won
   sem boas-vindas.
10. Ligação real (Pedro): número novo na linha principal atendida/perdida → 1 card em Pool Leads + tarefa (+ SMS se o V9
    missed estiver ligado); de um contato com `existing customer` → nada; na linha AdWords → só o fluxo da WC (1 card,
    pipeline antiga).
11. Apagar contatos/cards/tarefas/cópias de teste.

**Publicar (cada passo só depois do anterior conferido)**
12. Spam Contact, Recurring Customer Stage (sem mensagem) → Quote Sent, No Response, No-Show, Lost (guardados) →
    Answered/Missed Incoming Call (só principal) → decisão do nativo: se o Frank quiser o SMS do V9, **desligar o
    nativo** (`enableMissedCallText`, backup) e publicar o Missed New Lead SMS no mesmo minuto; senão o V9 Missed SMS
    fica draft → Won Stage (conforme decisão) → Contact Created -> add owner (se quiser dono automático) → o resto só
    quando houver uso (reactivation, review).
13. Dump + auditoria + 48 h de monitoramento (saídas para `pre-snapshot` = 0; cards duplicados = 0).
14. Reversão: cada workflow tem backup; voltar para draft e restaurar `enableMissedCallText` leva minutos.

### 5.2 Lakewood Ranch

1. Backup completo como na WC (`backup/poolduck-lakewood-ranch/pre-v9-<data>/`), incluindo os 2 workflows de review
   em andamento e os NPS.
2. Tags `pre-snapshot` (771) e `existing customer` (355 clientes: QuickBooks + `turtle rock`).
3. `pd_v9_port.py` (b) — **reaproveitando** NPS Score/NPS Message/NPS Form/NPS Survey Link da LWR (nada criado em cima).
   Tudo draft, com os guardas.
4. Ligações: a linha principal está no IVR ("Active - Phone Tree IVR") → todo atendimento vira "completed": o
   Answered do V9 dispararia para **todas** as ligações da principal e o Missed nunca. Opções: (i) V9 Answered/Missed
   só na linha do Google Ads — não, essa já tem o fluxo nosso → **deixar os dois em draft na LWR**; (ii) se o Frank quiser
   card de ligação da principal, marcar `missed call` dentro do IVR (padrão `pp_ivr_missed`) — é mudança no IVR da conta,
   só com OK.
5. Review: **V9 Review Request e Review Response em draft** enquanto a campanha Turtle Rock/NPS gate estiver ativa (e o
   Positive promete mês grátis por indicação — política a confirmar). Quando o GBP for ligado, as reviews da campanha
   disparariam o Review Response.
6. Restante igual à WC (pipeline Pool Leads ao lado; os 4 cards ficam onde estão; fluxos de Google Ads/comercial/FB
   continuam criando card na pipeline da LWR).
7. Testes em cópias + publicação na mesma ordem; nativo: mesma decisão do Frank.

### 5.3 Odessa

1. Backup completo. Tag `pre-snapshot` nos 328 (não há clientes; se houver lista de clientes fora do GHL, nada a fazer).
2. Pedro: Refresh do V9 → link → import na agência Pool Duck (admin) → **vigia ligado** → load na Odessa à noite,
   desmarcando funis/calendários, **sem overwrite** (Legal Business Name). Logo depois: conferir pelo dump que os 28
   chegaram em draft (o vigia pega os publicados) e que os 7 publicados da Odessa estão intactos.
3. Pela API (token Pool Duck, já com os ids convertidos pelo snapshot): usuários nos avisos/tarefas, custom values,
   guardas, `pp_tags_missing`, `pp_fix --drop-booking --include-drafts --skip "In Communication Stage"`.
4. Linha com encaminhamento → Answered/Missed funcionam como no modelo (guarda de `pre-snapshot` nas ligações de quem já
   ligou: 310 dos 328 são isso).
5. Testes em cópias, publicação na mesma ordem; nativo: decisão do Frank.

### 5.4 Ordem de publicação (as três)

1. Sem mensagem: Spam Contact, Recurring Customer Stage.
2. Etapas (só cards novos na Pool Leads): Quote Sent, No Response, No-Show, Lost.
3. Ligações: Answered/Missed Incoming Call (linha conforme a conta) → Missed New Lead SMS + nativo desligado (juntos).
4. Won Stage (boas-vindas conforme decisão) → Contact Created -> add owner.
5. Sob demanda: Reactivation (com tag combinada, não em massa sem aviso), Review Request/Response, 08 Paid Ads,
   03 Appointment, 06 Recurring.

### O que precisa de mão humana (Pedro)

- Refresh do snapshot V9 e o link de compartilhamento (Pool Profits) e o import/load na Pool Duck (admin da agência) — Odessa.
- Ligações de teste nas linhas (principal atendida/perdida, linha de anúncio) e envio real de form (Turnstile).
- Desligar o missed-call nativo se a API recusar (`PUT /locations/{id}` costuma funcionar).
- Explicar à equipe de cada franquia (pelo Frank) as duas pipelines e a tag `pre-snapshot`.

---

## 6. Perguntas para o Frank / Ed

1. Quem recebe os avisos/tarefas e quem é o "dono" automático do contato em cada conta?
2. Missed-call text: fica o nativo (hoje ligado nas 3, manda até para cliente) ou passa para o SMS do V9 (só lead novo)?
3. WC/LWR: os cards antigos ficam na pipeline atual (minha recomendação) ou migram para a Pool Leads (aí mexo nos fluxos
   de anúncio e na conversão do Google Ads)?
4. Boas-vindas ao cliente novo: a da Pool Duck (tag `new residential client`) ou o Won Stage do V9? Só uma.
5. Ligações: card/tarefa do V9 só na linha principal (as de anúncio já têm fluxo)? Na LWR, posso mexer no IVR para marcar
   ligação perdida?
6. Review: com a campanha da LWR no ar, o Review Request/Response do V9 fica desligado? A promessa "free month por
   indicação" vale para a Pool Duck?
7. A WC tem 4 workflows publicados em dobro (boas-vindas, link do form de orçamento, cartão recusado, chat) — o cliente
   novo recebe 2× hoje. Corrijo?
8. Os drafts da Pool Duck (nurture, aniversário/feriados, ZappyChat) continuam desligados?
9. Odessa: nome do dono para as mensagens e preços (se algum texto usar).
10. Acesso de admin da agência Pool Duck para importar o snapshot (Odessa) e janela de horário para cada conta.

---

## Rascunho de resposta ao Frank (EN — Pedro, 1ª pessoa)

> Hi Frank,
>
> I went through the three Pool Duck accounts before touching anything. Nothing has been changed yet.
>
> What I found:
> - **Wesley Chapel** is very much live: about 2,600 contacts (around 1,200 are customers synced from QuickBooks),
>   ~200 new contacts in the last 30 days, 97 open lead cards, 4 phone lines with their own call/ad automations.
> - **Lakewood Ranch**: ~770 contacts (about 355 customers), 4 open cards, the IVR on the main line and the review
>   campaign still running.
> - **Odessa**: ~330 contacts, almost all just callers, no customers and no cards.
> - The native missed-call text is on in all three, so any missed call (customers included) already gets a text today.
>
> The main risk with a plain snapshot import is that the V9 call workflows listen to every inbound call on every line.
> In Wesley Chapel that would put existing customers into the new pipeline as "new leads", text them after a missed
> call, and create a second card for every ad call. A snapshot load into a live account can also bring workflows in
> published for a few seconds.
>
> My plan:
> - Back up each account in full first.
> - Tag every existing contact (`pre-snapshot`) and every customer (`existing customer`). Every V9 trigger gets a
>   "doesn't have tag" guard, so nothing can reach anyone who is already in the account.
> - Everything from V9 lands as draft.
> - Odessa: import through the shared snapshot link, at night, with a watcher that drafts anything arriving published.
> - Lakewood Ranch and Wesley Chapel: copy V9 over through the API, so nothing is ever published by the import and
>   nothing they already have is overwritten (Lakewood's NPS fields and review campaign stay as they are).
> - Wesley Chapel's current cards stay in their current pipeline, and the team keeps working them exactly as today.
> - I publish one workflow group at a time, and only after I've tested it on test copies. Test contacts get deleted.
>
> A few decisions I need from you or Ed before I start:
> 1. Who should get the lead alerts and tasks in each account?
> 2. Keep the native missed-call text, or switch to the V9 one (new leads only)?
> 3. Should Wesley Chapel's existing cards stay in their current pipeline, or move to the V9 pipeline? Moving them means
>    I also have to repoint their ad workflows and the Google Ads conversion.
> 4. Which welcome message should new customers get: Pool Duck's current one or the V9 Won Stage? Only one of them
>    should run.
> 5. Should the V9 call workflows run on the main line only? The ad lines already have their own flows.
> 6. Should the V9 review workflows stay off while Lakewood's review campaign is running?
>
> One more thing I noticed: Wesley Chapel has four workflows published twice (welcome, quote form link, card
> declined, chat alert), so new customers get the welcome email and text twice right now. I can fix that if you'd
> like.
>
> Once I have your answers, I'll set up a time window for each account and send you the schedule.
>
> Pedro
