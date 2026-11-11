# TODO do Pedro — só o aberto (10/11/2026)

Curto de propósito (as rotinas leem este arquivo). **Regra das tarefas do ClickUp (Pedro 10/11)**: toda tarefa que eu crio
tem prazo realista e é fechada quando o meu trabalho está feito e testado; se só falta teste real do Pedro, comento, fecho
e acrescento o teste no checklist da tarefa única "Live tests with Pedro" (`86bd1b3b5`); se depende de outra pessoa,
comento quem/o quê e ajusto o prazo — nada fica vencido sem dono. Uma linha por item; detalhe e histórico em
`docs/execucao-*.md` e `docs/TODO-arquivo-2026-11-04.md`. Item fechado sai daqui. Teste que avisa cliente:
combinar antes.

## Você faz
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
9. **Contas fora do modelo (Frank 10/11)** — `scripts/pp_fleet_check.py`; detalhe no fim de
   `docs/execucao-2026-10-27-clearpool-dash.md`. Migradas: Corolla, Aqua Clear, YardSpring, Bluebird e Summer Wave (as duas
   em draft). **Seu**: 27 contas pré-V9 (snapshot de antes do V9) só migram com os custom values do cliente preenchidos
   (nome do dono, telefone, e-mail, preço semanal, link de agendamento, número do A2P, link do Google) e decisão sobre a
   linha/IVR de cada uma — via Frank ou questionário; confirmar quais ainda são clientes (Net Positive, Next Level, Pooly,
   Ponchos sem usuário; GID e Next Level sem lead novo desde 03/2026 e 12/2025). Pool Smart OC meio migrada (fluxos ao lead em
   draft, faltam 5 custom values). Fora por configuração própria: BluVantage, Clear Pool, Ekahi, Sunwave, Pool Palooza,
   Golden View, Pool Duck.
10. **Gate de nota** (Frank 10/11): só 5 recebe o link do Google; 1–4 recebe SMS "what could we have done better?" +
   aviso à equipe (`pp_review_gate.py`). Sem nota em 7 dias → recebe o link, como no V9 (Pedro 11/11: manter).
10b. **E-mail do novo processo para Ed/Frank/Jonathan** (ClickUp `86bd1ctcg`): texto em `docs/team-email-new-account-process.md`;
   a rodada diária envia sozinha quando: 1º A2P automático aceito (Corolla aprovada 11/11, mas enviada pela tela) + guia do CRM enviado automático + usuário criado
   automático + Refresh do snapshot. **Seu**: aprovar o texto do e-mail do guia ao cliente (`config/crm_guide_email.json`,
   `approved: true`) e o Refresh do snapshot (item 4).
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
