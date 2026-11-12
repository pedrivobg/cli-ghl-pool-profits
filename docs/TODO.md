# TODO do Pedro — só o aberto (11/11/2026, revisão da noite)

Curto de propósito (as rotinas leem este arquivo). **Regra das tarefas do ClickUp (Pedro 10/11)**: toda tarefa que eu crio
tem prazo realista e é fechada quando o meu trabalho está feito e testado; se só falta teste real do Pedro, comento, fecho
e acrescento o teste no checklist da tarefa única "Live tests with Pedro" (`86bd1b3b5`); se depende de outra pessoa,
comento quem/o quê e ajusto o prazo — nada fica vencido sem dono. Uma linha por item; detalhe e histórico em
`docs/execucao-*.md` e `docs/TODO-arquivo-2026-11-04.md`. Item fechado sai daqui. Teste que avisa cliente:
combinar antes.

## Regras da rotina (lidas a cada disparo; Pedro 11/11)
- **ClickUp não tem API de "marcar como lido"** (chat, respostas, Inbox, notificação de tarefa). Depois de responder ou
  terminar uma mensagem de chat/resposta em thread, pôr a reação `white_check_mark` nela (`clickup_react_to_chat_message`):
  o Pedro vê o que já foi tratado e usa "Mark all as read". Nunca reagir no que ainda precisa dele.
- **E-mail do guia do CRM ao cliente** (`config/crm_guide_email.json`): só envia com `approved_pedro` e `approved_frank` =
  true. Pedro aprovou 11/11; se o Frank responder "approved" no e-mail "[Approve] CRM guide e-mail to clients" → pôr
  `approved_frank: true`, commit, e a rodada diária passa a mandar.
- **Nada pode disparar para contato/lead/cliente antigo** (Ed e Pedro 11/11; WC da Pool Duck tem leads reais): não mover
  card, não publicar fluxo novo, não pôr tag que tenha gatilho, não importar lista sem OK. Migração de conta antiga =
  `scripts/pp_fleet_migrate.py` (fluxo existente mantém o status; novo entra draft).
- Item de e-mail que o Pedro não respondeu = fica como está até ele decidir.
- **Regra dos 5 minutos é da resposta, não da captação** (Pedro 11/11): o n8n capta e manda na hora; a rotina nunca
  posta resposta a uma pessoa (ClickUp, e-mail, Basecamp) menos de 5 min depois do `received_at` do item — terminou
  antes, espera o que falta e então posta (resposta em cima da mensagem entrega que é automático).
- **Resposta do guia do CRM = decisão do cliente** (Pedro 11/11): aplicar direto, sem "[Aprovar]". Texto que o cliente
  mudou → usar o dele. "SIM" para algo que pede texto novo (ex.: boas-vindas de reparo/obra) → usar o padrão já aprovado
  (o da Corolla, com nome/telefone/e-mail da conta) e avisar o Frank. Só vai ao Pedro o que for ambíguo ou fora do padrão.

## Você faz
0. **BluVantage**: resolvido. Resposta à Vanessa enviada 12/11 14:03 UTC; ligação real 12/11 8:51 ET passou pelo
   "Sequential Call Routing" (v19) e a Vanessa atendeu (2 min). Ligação de teste sua não é mais necessária.
1. **Tokens**: trocar os refresh tokens que mostrei no chat (Pool Profits, Pool Duck, BurchTech, Poolheads antiga) e as
   Application Passwords; depois abrir uma sessão nova → eu testo as variáveis e recrio a auditoria de quinta lá.
2. **Pool Duck snapshot** (ClickUp `86bcxzjfa`, prazo 05/11): revisar `docs/poolduck-snapshot-plan.md` e mandar ao Frank.
3. **Contas novas (processo automático desde 10/11, `docs/new-account-review.md`, SOP em `docs/a2p-sop.md`)**: Smart Chem,
   West Coast e Capital prontas (0 ALTA/0 ERRO, usuário do dono em avisos/tarefas, guia do CRM com o Frank). O **1º número**
   de cada conta é do Frank/time (Pedro 11/11: não é item seu; a rodada diária avisa o Frank). Mako's Pool, Cool N Clean,
   Puddle Jumper e Pools of Perfection responderam só o "Training Survey Intake Form": falta o questionário 2.0.
4. **Refresh do snapshot V9** (na tela).
6. **Testes reais**: todos numa tarefa só, com checklist — ClickUp [Live tests with Pedro](https://app.clickup.com/t/86bd1b3b5)
   (prazo 14/11). YardSpring: os 3 números já encaminham para o Joe (Ed's number gravado 10/11 por API).
7. **Na tela**: Call Recording Poolheads; Tiffany (WP Pools) telefone no usuário; LWR Google Lead Ads → mapear e ativar
   o form "Weekly pool service done right".
8. **Blue Lagoon** (86bcyu05g): o rascunho da oferta de $250 para a Caila não está mais nos rascunhos do Gmail — se já foi,
   fechar a tarefa; se não, me avisa que eu refaço.
9. **Contas antigas no modelo (11/11)**: 34 migradas com status mantido (log 11/11). **Para ver com o time** (fluxo próprio
   da conta, não mexi): Damon's, Clean Co, Ponchos, Ekahi, Pooltexx, Wrigley's, BluVantage, Clear Pool; e Pool Palooza, Golden
   View, sub-conta Pool Duck (estrutura diferente). Dados do cliente vazios ficam para depois (Pedro 11/11).
9b. **Pool Duck** (respostas do Ed 11/11, thread "Pool Duck Franchisee Accounts"): tudo para a Pool Leads (cards, fluxos de
   anúncio, conversões do Google Ads, Review Request nas etapas Won; campanha de review da LWR intocada), SMS de missed do V9
   no lugar do nativo, card de ligação só na linha principal, marcador `missed call` no IVR da LWR, boas-vindas = tag
   `new residential client` (duplicada da WC desligada 11/11), avisos = as mesmas pessoas de hoje. Free month: tirado do
   "In Communications" antigo (30 drafts); **faltam os 3 publicados** (Pool Time, Reign, Sparkling Clear) — `pp_referral_offer_fix.py`
   bloqueado pelo classificador; Ed avisado que sai amanhã cedo. Fase 2 LWR + Odessa 12–13/11; WC depois da resposta
   do dono (via Frank), após 18h ET. Você: aprovar o e-mail ao Matt (preços da Odessa; dono = Matt já gravado).
10. **Gate de nota** (Frank 10/11): só 5 recebe o link do Google; 1–4 recebe SMS "what could we have done better?" +
   aviso à equipe (`pp_review_gate.py`). Sem nota em 7 dias → recebe o link, como no V9 (Pedro 11/11: manter).
10b. **E-mail do processo novo para Ed/Frank/Jonathan**: enviado 11/11. Quando o 1º A2P automático for aprovado → uma
   linha no mesmo thread ("GHL update: one snapshot for every client…") dizendo que está 100% no ar (ClickUp `86bd1ctcg`).
11. **API do Claude no n8n** (Pedro vai colocar, 10/11): credenciais "Anthropic Pool Profits" (chave da API) e "GHL Agency
   Token" (Header Auth com o refresh token do GHL) → eu monto o agente do n8n com ferramentas limitadas (custom value,
   texto de template de SMS, tag, resposta no ClickUp) para os itens fáceis do inbox, testo na Test Snapshot e ligo.

## Esperando outros
- Felipe (Poolheads, via Frank): histórico como nota?, webhook "LVB - Meta Service", usuário do Jorge.
- Atif: páginas/obrigado de Poolheads, Pool Shack, YardSpring, BluVantage; tirar o número antigo da página Weekly da NorTex.
- Val: Google Ads conectado (Poolheads, Pool Shack, YardSpring) e acesso para o Send Data dos Google Lead Forms.
- Frank: Stay Fresh (avisos de ligação para o Kris, re-entry, IVR, lista de inativos); Pool Shack (retorno do Rob);
  tags universais; Pool Keepers (o que liga); GBP da Clear Pool no número de rastreamento.
- Derek (Clear Pool): publicar Review Request?, chave do Pool Brain. Erik (Ekahi) e Jeremy (SwimReady): ajustes por código.

## Em breve (combinado)
- **Dashboard interno** (Val, 06/11 e 09/11): auditoria diária de todas as sub-contas para prever erros (alertas/tarefas
  sem usuário, linhas sem encaminhamento, SMS falhando, gatilhos quebrados) e acompanhar quem não está recebendo leads
  ou não está usando o CRM (0 lead em 3 dias, WON, cards parados). ClickUp: tarefa "Internal dashboard: daily GHL audit".
