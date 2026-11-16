# Pauta — Pool Duck Wesley Chapel (16/11, 14h15 CST, Ed + dono + Pedro)

Objetivo (Ed, call da manhã): passar pela conta da WC, ver leads, consertar automações, importar automação, ensinar o dono a
usar e anotar customizações. Auditoria ao vivo de 16/11 ~20h UTC (dump `dump/poolduck/pool-duck-wesley-chapel`).

## 1. Leads e uso do CRM (mostrar primeiro — é o que mais dói)
- **108 cards abertos, todos em "Lead"**: nenhum card nunca foi movido de etapa. 13 novos em 14 dias (5 ligação Google
  Ads, 5 form do Facebook, 2 LSA, 1 form Google Ads) — 11 deles **sem responsável**.
- Sem mover card, o Google Ads não recebe sinal de cliente ganho/perdido e otimiza no escuro (mesmo caso da Reign).
- **Mensagens sem resposta agora** (mostrar na tela, Conversations):
  - **Joni Hancock** (13/11, 3 dias): "Can you listen to my msg and reply pls" — deixou recado e ninguém voltou.
  - **Kathy Owen** (hoje, cliente): "Your company has been drafting from our account but you didn't this month" (cobrança,
    endereços 34312 e 34315 Smart Drive, Zephyrhills) — ligação dela virou card de lead novo (cliente tratada como lead).
  - **Saleena Niehaus** (hoje): quer orçamento semanal, mas é de **Odessa** → mandar para a franquia de Odessa.
  - **Michele Gaster** (13/11, webchat): "How do I sign in to my account?" — o link do portal PoolBrain está vazio na conta.
  - Contato comercial (+1 512-886-0277): piscinas comerciais em Cape Coral/Deland/Fort Myers.
- Perguntar: quem responde texto/ligação no dia a dia? Usam o app no celular? Recebem os avisos?

## 2. Ligações
- 4 linhas (Pool Duck principal 813-606-0773, AdWords 813-815-7946, LSA 813-934-7946, Facebook 813-670-3825):
  **nenhuma encaminha para celular e nenhuma tem menu** → só tocam no app. 23 ligações de entrada em 7 dias.
- Decidir: para qual celular cada linha toca (Debbie? Justin? os dois em sequência?) e se quer menu "aperte 1" contra spam.
  Faço na hora e testo com uma ligação.

## 3. Avisos internos que não chegam em ninguém
- "Steve" **não existe** como usuário na conta (usuários: Debbie ×2 — service@ e debbie@, Justin, Preston ×2 — um sem
  telefone). Publicados sem destinatário: "New Pool Quote Request Form Submitted - Residential - Steve" (3 SMS),
  "Pool Quote Request Form Submitted - Steve", "Pool Quote Request Form Submitted - Debbie" (notificação sem usuário),
  "Message via Chat Widget notification" (cópia 2 sem usuário).
- Decidir: quem recebe cada aviso (form do site, webchat, chat widget). Sugestão: Debbie + Justin em todos.
- Usuários duplicados (2 Debbie, 2 Preston): qual login fica?

## 4. Automações publicadas em dobro (cliente recebe 2×)
- "Credit Card / ACH update request workflow" (2 cópias), "Send Pool Service Quote Form Link" (2), "Message via Chat Widget
  notification" (2). A boas-vindas duplicada já foi desligada em 11/11.
- Pedir OK para pôr a cópia extra de cada em draft (1 minuto, com backup).
- Cartão/ACH: o texto usa `{{custom_values.pool_brain_customer_portal_link}}`, **vazio** → cliente recebe o SMS sem link.
  **Pegar o link do portal PoolBrain** (pelo e-mail da Michele parece ser `poolduck.poolbrain.com`) e o **link de review do
  Google** (custom value "Public Review Link" também vazio).

## 5. Snapshot V9 (o que "importar automação" quer dizer)
- Plano já mandado ao Frank/Ed (`docs/poolduck-snapshot-plan.md`): copiar o V9 pela API **sem publicar nada**, guardas para
  cliente antigo (tags `pre-snapshot` / `existing customer`), pipeline "Pool Leads" ao lado da atual.
- Ganho para ele: follow-up automático de lead que some, lembrete de orçamento enviado, review só com nota 5, card criado
  em toda ligação/form, aviso por SMS de todo texto recebido, dashboard padrão.
- Decidir com o dono: (a) os 108 cards ficam na pipeline atual ou vão para a nova; (b) o que publicar primeiro;
  (c) cliente antigo nunca recebe nada (confirmar). Fase 2 de LWR/Odessa também espera esta conversa.
- Meta: a conta de anúncio selecionada na integração é "Justin Denham", não "Pool Duck Wesley Chapel" — confirmar qual
  roda os anúncios da WC (o dashboard mostra o gasto da selecionada).

## 6. Ensinar (10 min no fim)
- Conversations (responder SMS/webchat/Facebook num lugar só), Opportunities (arrastar o card: Engaged → Call Booked →
  Customer / Didn't Sign Up / Bad Fit), app no celular com notificações ligadas.

## Anotar na reunião
- Celular de cada linha · quem recebe cada aviso · link PoolBrain · link de review · OK para desligar as cópias ·
  decisão do V9 / cards · conta do Meta · qualquer texto que ele queira mudar.
