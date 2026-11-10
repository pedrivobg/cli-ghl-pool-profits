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
   West Coast e Capital prontas (0 ALTA/0 ERRO, usuário do dono em avisos/tarefas, guia do CRM com o Frank). Falta de você:
   **1º número** de cada uma (o GHL pede documento + selfie só na 1ª compra; eu compro os outros 2, nomeio e encaminho) —
   Smart Chem 512, West Coast 323, Capital 916. Via Frank: logo da Smart Chem, GBP de Smart Chem e West Coast, primeiro acesso
   (Steve, Milen, Zuriel). Mako's Pool, Cool N Clean, Puddle Jumper e Pools of Perfection responderam só o "Training Survey
   Intake Form": falta o questionário 2.0 (é ele que cria a sub-conta).
4. **Refresh do snapshot V9** (na tela).
5. **Corolla A2P**: go.corollapoolandspa.com conectado e DNS certo, mas o GHL não emite o SSL (erro cinza, mesmo apagando e
   adicionando de novo) → ticket no suporte do GHL ou testar outro subdomínio (CNAME `sms` no Wix). Links e campanha já
   corrigidos para a raiz (sem /pools); a rodada diária envia quando abrir. 1º número também em Rosebrook, WP Pools, Bonneville.
6. **Testes reais**: todos numa tarefa só, com checklist — ClickUp [Live tests with Pedro](https://app.clickup.com/t/86bd1b3b5)
   (prazo 14/11). YardSpring: os 3 números já encaminham para o Joe (Ed's number gravado 10/11 por API).
7. **Na tela**: Call Recording Poolheads; Tiffany (WP Pools) telefone no usuário; LWR Google Lead Ads → mapear e ativar
   o form "Weekly pool service done right".
8. **Blue Lagoon** (86bcyu05g): o rascunho da oferta de $250 para a Caila não está mais nos rascunhos do Gmail — se já foi,
   fechar a tarefa; se não, me avisa que eu refaço.
9. **Corolla → migrar para o modelo (decisão sua, 10/11)**: o cliente aprovou as 24 mensagens do guia, mas o que está no
   ar é a carga V9 antiga de 30/09 + 6 fluxos extras publicados (In Communication manda 3 e-mails; Monthly Service Reminder
   leva cliente pagante para a cadeia de "lead perdido"; Filter Clean, Upsell, Post-Appointment, Appointment). Com o seu OK:
   `pp_mirror --apply` + sequência de onboarding (missed-call nativo off) + reaplicar janelas 08–18 + boas-vindas de reparo
   (textos prontos, aprovar) — antes de importar a lista de clientes. Feito hoje: usuário Josh (admin), Sequential Call
   Routing da BluVantage → draft, janelas 08–18 em Won/Lost/Review, link de review da Clear Pool → o da Corolla.
10. **Contas no snapshot antigo** (Pool Palooza, Corolla, Aqua Clear, ABC, Clear Conceptz, Pool Smart OC…): decidir com o
   Frank quais migram para o V9 (ClickUp 86bcz86jw).

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
