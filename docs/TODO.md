# TODO do Pedro — só o aberto (16/11/2026, revisão geral do ClickUp)

Curto de propósito (as rotinas leem este arquivo). **Regra das tarefas do ClickUp (Pedro 10/11)**: toda tarefa que eu crio
tem prazo realista e é fechada quando o meu trabalho está feito e testado; se só falta teste real do Pedro, comento, fecho
e acrescento o teste no checklist da tarefa única "Live tests with Pedro" (`86bd1b3b5`); se depende de outra pessoa,
comento quem/o quê e ajusto o prazo — nada fica vencido sem dono. Uma linha por item; detalhe e histórico em
`docs/execucao-*.md` e `docs/TODO-arquivo-2026-11-04.md`. Item fechado sai daqui. Teste que avisa cliente:
combinar antes.

## Regras da rotina (lidas a cada disparo; Pedro 11/11)
- **Marcar como lido no ClickUp é obrigatório** (Pedro 17/11: "está ficando uma bagunça"). Depois de responder/resolver um
  item do ClickUp: `python3 scripts/cu_mark_read.py --channel <canal/DM> --thread <parent do thread> --task <task>` (ids
  vêm do payload: `cu-chat-<msg>` + `parent=`, `task=`; o canal sai da url `/chat/r/<canal>`). Marca DM/canal, thread e
  comentários como lidos e tira a tarefa do Inbox (read + clear). No fim da rodada: `--clear-activity --older-hours 24`.
  Nunca marcar o que ainda precisa do Pedro. Saída 2 = token da sessão do ClickUp expirou → e-mail
  "[Passo seu] ClickUp: renovar o token" com os passos de `docs/inbox-watch-routine.md` (seção "Marcar como lido").
- **Arquivo achado em qualquer lugar = eu baixo** (Pedro 17/11, West Coast: a rotina pediu ao Frank para reanexar um xlsx
  que estava no Basecamp, no e-mail e na tarefa). Nunca dizer "não consigo baixar daqui" nem pedir para mandarem em outro
  lugar. Antes, tentar todos os caminhos: (1) **e-mail de notificação do Basecamp** → `get_message` (html) → link
  `https://storage.app.basecamp.com/.../email/download/.../<arquivo>` = assinado, `curl -sSL` baixa sem login (testado
  17/11); (2) anexo do Gmail → `download_gmail_attachment`; (3) anexo de tarefa ClickUp → `clickup_download_task_attachment`;
  (4) `Basecamp download_file` (texto/imagem só). Se nada der: **perguntar ao Pedro** (e-mail [Passo seu]), nunca ao time
  nem ao cliente — para eles o Pedro e eu somos um só.
- **Aprovação do time vale** (Pedro 13/11): mensagem com contexto claro e sem dúvida, que alguém do time (Frank, Val, Ed)
  já pediu ou aprovou, vai direto — inclusive para cliente — sem "[Aprovar]" para o Pedro (senão espera ~2 h). Só vai ao
  Pedro o que for ambíguo, novo, sensível (reclamação, preço, culpa) ou sem aprovação de ninguém do time.
- **Reações no ClickUp: NÃO reagir em toda mensagem** (Pedro 12/11: reagir em tudo com ✅ parece automação). Reação não
  marca como lido. Só de vez em quando, como uma pessoa
  faria, quando combina (pedido recebido/feito, agradecimento): variar `thumbsup`, `white_check_mark`, `saluting_face`.
  No normal, a resposta escrita basta. Nunca reagir no que ainda precisa do Pedro.
- **E-mail do guia do CRM ao cliente** (`config/crm_guide_email.json`): só envia com `approved_pedro` e `approved_frank` =
  true. Pedro aprovou 11/11, Frank aprovou 13/11 (`approved_frank: true`): a rodada diária já manda por e-mail.
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

- **Chave do guia do CRM** (Pedro 17/11: automático em qualquer sessão): `CRM_GUIDE_ADMIN_KEY` fora do ambiente → ler do
  workflow n8n `SlfpWZmKH1d62hB9`, nó "Check admin key", e passar só no comando (nunca gravar/logar). Nunca pedir ao Pedro.
- **Só respondo quando me marcam ou é assunto do CRM/GHL** (Pedro 17/11): mensagem no Basecamp/e-mail do cliente para o
  Frank/time sobre site, GBP, design etc., sem me marcar → não responder nem mandar "[Aprovar]"; só marcar como lido.
- **Pergunta ao time sem resposta** (Pedro 16/11): passou 2 dias úteis → 1 mensagem só ao Frank/Val/Ed com a lista do que
  falta (não pergunta por pergunta) e o item entra no e-mail do Pedro. Nunca empurrar prazo de tarefa sem cobrar o dono.
- **Toda tarefa atribuída ao Pedro em qualquer lista** (onboarding do Frank, Paid Media, Create GHL Account) entra na revisão
  da noite — não só a lista `901422915733`. Tarefa nova do Frank: comentar no mesmo dia (feito / o que falta / de quem).

## Você faz
B. **West Coast A2P recusado** (16/11, 1ª recusa: nome legal ≠ EIN). 17/11 noite: nome legal **MFD Racing, Inc.** (S-Corp, DBA
   West Coast Pool Care, EIN 37-2238084, Milen) no perfil + custom value (privacy/terms/rodapé do go.) + campanha. Falta o
   **endereço do EIN letter** (pedido ao Frank no Basecamp interno; hoje PO BOX 2136) → reenviar no mesmo dia, sem novo OK
   (`pp_a2p.py submit`). 3ª recusa bloqueia → se recusar de novo, avisar o Pedro antes de tudo. ClickUp `86bd3m8c9` (20/11).
C. **Pool Duck**: Wesley Chapel no V9 desde 16/11 (log; `scripts/pd_wc_phase2.py`). Follow-up quinta 19/11 15h (Justin/Ed/Frank):
   respostas do guia (`pool-c81cf184`), NPS form + Review Request, Won welcome. LWR/Odessa: mesma fase 2 depois disso.
0. **[Aprovar] Bonneville – número do Google Ads** (14/11, Val aprovou comprar): eu não compro número sem o seu OK (ação
   paga). Responder "aprovado" → compro um 385 (ex.: +1 385-365-2440), nome "Google Ads", encaminha para o Justin, passo ao
   Atif para trocar nas LPs. ClickUp `86bd2ha9z`.
1. **SMS de teste para a Sparkling** (e-mail "[Passo seu] Teste do alerta de SMS recebido", 13/11): mandar "teste" do seu celular para +1 469-617-2308 e responder "feito" → eu rodo `pp_sms_alert.py testcheck` e `apply --all`. Refresh do snapshot (master ganhou "Inbound SMS - Notify Owner"). ClickUp `86bd349d8`.
(12/11: tokens trocados, Refresh do snapshot feito 11/11 e 12/11, Call Recording Poolheads, form da LWR no Lead Ads,
prompt novo da rotina colado — feitos pelo Pedro. Próxima sessão nova: conferir que as variáveis de token funcionam.)
2. **Pool Duck snapshot** (ClickUp `86bcxzjfa`, prazo 05/11): revisar `docs/poolduck-snapshot-plan.md` e mandar ao Frank.
3. **Contas novas (processo automático desde 10/11, `docs/new-account-review.md`, SOP em `docs/a2p-sop.md`)**: Smart Chem,
   West Coast e Capital prontas (0 ALTA/0 ERRO, usuário do dono em avisos/tarefas, guia do CRM com o Frank). O **1º número**
   de cada conta é do Frank/time (Pedro 11/11: não é item seu; a rodada diária avisa o Frank). Mako's Pool, Cool N Clean,
   Puddle Jumper pronta 12/11 (falta 1º número/Frank, DNS do cliente, link de review). Pools of Perfection: criada 13/11 pela API com o V9 (pronta;
   falta número/A2P/link de review). Guia publicado (`crm-guide?c=pools-33d2dc4b`, já em crm_guide_links → a rodada não
   reenvia): **Ed 13/11: segurar** (rascunho do site primeiro, depois falar com ele; `hold` no crm_guide_email.json) → só mandar quando o Ed/Frank liberarem. Mako's Pool e Cool N Clean: falta o questionário 2.0.
6. **Testes reais** (Pedro faz 12/11 à tarde): ClickUp [Live tests with Pedro](https://app.clickup.com/t/86bd1b3b5), lista
   enxugada 12/11 (YardSpring, BluVantage linha principal e NorTex saíram; entrou o envio real das 2 LPs da Corolla). Depois de cada um: conferir os logs e apagar o teste.
9. **Contas antigas no modelo (11/11)**: 34 migradas com status mantido (log 11/11). **Para ver com o time** (fluxo próprio
   da conta, não mexi): Damon's, Clean Co, Ponchos, Ekahi, Pooltexx, Wrigley's, BluVantage, Clear Pool; e Pool Palooza, Golden
   View, sub-conta Pool Duck (estrutura diferente). Dados do cliente vazios ficam para depois (Pedro 11/11).
9b. **Pool Duck** (respostas do Ed 11/11, thread "Pool Duck Franchisee Accounts"): tudo para a Pool Leads (cards, fluxos de
   anúncio, conversões do Google Ads, Review Request nas etapas Won; campanha de review da LWR intocada), SMS de missed do V9
   no lugar do nativo, card de ligação só na linha principal, marcador `missed call` no IVR da LWR, boas-vindas = tag
   `new residential client` (duplicada da WC desligada 11/11), avisos = as mesmas pessoas de hoje. Free month: tirado do
   "In Communications" antigo (30 drafts); **3 publicados** (Pool Time, Reign, Sparkling Clear): Pedro 12/11 = mudar texto ao
   vivo de cliente só com OK → perguntado ao Frank (DM 12/11) se algum dos 3 pediu a oferta; com o OK dele →
   `pp_referral_offer_fix.py config/referral_offer_live.json x --apply`. Fase 2 LWR + Odessa 12–13/11; WC depois da resposta
   do dono (via Frank), após 18h ET. E-mail ao Matt (preços da Odessa) enviado 12/11; esperando resposta.
10. **Gate de nota** (Pedro 17/11: **4 ou 5** recebe o link do Google; 1–3 recebe SMS "what could we have done better?" +
   aviso à equipe; `pp_review_gate.py`, aplicado 17/11 em todas + Snapshot; guias novos com o texto 4–5, os antigos ficam). Sem nota em 7 dias → **sem link** (Ed 13/11; feito 16/11 em todas + Snapshot,
   `pp_review_noscore.py`, testado; Clear Pool fica de fora: fluxo próprio em draft).
10b. **E-mail do processo novo para Ed/Frank/Jonathan**: enviado 11/11. Quando o 1º A2P automático for aprovado → uma
   linha no mesmo thread ("GHL update: one snapshot for every client…") dizendo que está 100% no ar (ClickUp `86bd1ctcg`).
11. **API do Claude no n8n** (Pedro vai colocar, 10/11): credenciais "Anthropic Pool Profits" (chave da API) e "GHL Agency
   Token" (Header Auth com o refresh token do GHL) → eu monto o agente do n8n com ferramentas limitadas (custom value,
   texto de template de SMS, tag, resposta no ClickUp) para os itens fáceis do inbox, testo na Test Snapshot e ligo.

12. **17/11 noite**: [Aprovar] resposta ao Justin (Pool Duck WC, guia + Terms of Service); Refresh do snapshot (Service
   Agreement Example); [Passo seu] ligação de teste nas 2 linhas novas da WP Pools.
13. **Reign LPs** (`86bd2jrc6`): prometido à Val preparar o lado GHL enquanto o Atif desenha (form com ZIP das 8 áreas, tags
   dos 3 serviços, origem Ads x GBP, etapas Spam/Not Qualified, avisos ao Stephen).

## Esperando outros
- Pedro (18/11): [Aprovar] Sunwave (Marketing IVR do David desliga quem não aperta tecla; No Response fica off); horário da
  call com o Nathan (Pool Keepers, qua–sex PT); apagar post interno duplicado no Basecamp Poolheads.
- Todd (Pool Palooza, 18/11): OK para o fluxo "Lead Source - Tag" por UTM/gclid + troca de número nas 3 páginas do Meta (`86bd4kerf`).
- Frank (17/11): Passion — avisos de lead de volta (18/11, `pp_passion_alerts_on.py`: 9 publicados, SMS ao lead tirado dos 3
  AdWords); textos/e-mails a cliente seguem off; WP Pools só 2 linhas por enquanto (3ª quando começar ads); Service Agreement Example na West Coast (ofereci colocar).
- Frank: e-mail/celular do Brad
  (Passion) para os avisos. Pool Keepers/Skimmer (17/11): a certa é a KjLd (BurchTech); Pedro criou a chave, Location ID + chave novos mandados ao
  Nathan por e-mail e Basecamp pedindo dia/hora da call. Esperando o Nathan trocar no Skimmer → conferir a conexão na KjLd
  e tirar a chave antiga da hh6X9 (Private Integrations, tela).
- Pedro (13/11): Pools of Perfection criada pela API; resposta ao Nathan (Skimmer nativo) e reunião de segunda aprovadas →
  extensão (prompt 2) posta; OK para pôr em draft as 2 cópias extras de Website Form Fill/Review Request da Clear Conceptz.
- Frank (12/11 noite): se o Brett apaga cards de lead da Southern (2 leads do Google Ads sem card, `86bd2t1kt`, 17/11).
  Padrão Skimmer para clientes mandado a ele (Enterprise = API; outros = Zapier só Skimmer→GHL; form do GHL fica no site).
- Felipe (Poolheads, via Frank): histórico como nota?, webhook "LVB - Meta Service" (único que falta antes de cancelar a conta antiga; 5 e-mails + 9 SMS conferidos na nova 17/11 com o token do ambiente), George como 2º toque 25 s/20 s (Frank pediu no Basecamp 16/11)
  (nome/e-mail/celular), página de privacidade, lista de clientes; Skimmer add-on → aí crio o token (Private Integrations,
  tela) e mando ao Felipe com o Location ID. Review Request da Poolheads fica draft (reviews no Skimmer). Calendário Leak
  Detection pronto e inativo: ligar na virada.
- Frank: dono para o alerta de SMS na Stay Fresh e na Blue Lagoon (as outras 8 sem dono estão inativas →
  `config/inactive_accounts.json`, puladas pelo `pp_sms_alert --all`); textos dos 8 posts de GBP da BluVantage (`86bd1xdbu`, 17/11).
- Frank (16/11): Pool Smart OC ainda é cliente? (fora da lista de inativos até ele confirmar; Ads precisa reconectar, `86bd1zk8p`).
- Val: Google Ads da Bonneville (conversão das 2 LPs novas). LPs/obrigado da Bonneville no ar (Atif 13/11), forms certos e
  redirect conferidos.
- Atif: páginas/obrigado de Poolheads, Pool Shack, YardSpring, BluVantage; tirar o número antigo da página Weekly da NorTex.
- Val: Google Ads conectado (Poolheads, Pool Shack, YardSpring) e acesso para o Send Data dos Google Lead Forms.
- Frank: Stay Fresh (avisos de ligação para o Kris, re-entry, IVR, lista de inativos); Pool Shack (retorno do Rob);
  tags universais; Pool Keepers (o que liga); GBP da Clear Pool no número de rastreamento.
- Frank (12/11): OK para o filtro de spam do form da Passion (telefone sem +1 / palavras de venda → spam, sem aviso; telefone só EUA)
  — 6 de 8 submissões em 30 dias eram spam; data da call da Reign → eu monto a tag `pipeline cleanup` (guarda nos fluxos de etapa).
- Derek (Clear Pool): publicar Review Request?, chave do Pool Brain. Erik (Ekahi) e Jeremy (SwimReady): ajustes por código.

## Em breve (combinado)
- **Ligações e SMS de todo cliente** (Ed 13/11, `86bd349d8`): depois do teste, `pp_sms_alert.py apply --all` (+ `pp_tags_missing`); dono das contas sem usuário com telefone (Stay Fresh, Blue Lagoon, Ponchos…) → Frank; linhas com IVR em draft (Dream Pools, Ponchos, Precision) → proposta ao Pedro antes de mudar encaminhamento. Linhas que só tocam no app (Aqua Clear, Clean Co, GID, Pool Palooza, Pool Keepers, Wrigley's) ficam assim (Pedro 17/11: decisão dos clientes).
- **Monitor de leads** (Frank/Val, Ed aprovou 13/11, `86bd349dt`, 18/11): alerta de card parado 3/4/5 dias + resumo a cada 3 dias dos clientes de Google Ads (tudo interno). 1º resumo no thread no começo da semana.
- **Dashboard interno** (Val, 06/11 e 09/11): auditoria diária de todas as sub-contas para prever erros (alertas/tarefas
  sem usuário, linhas sem encaminhamento, SMS falhando, gatilhos quebrados) e acompanhar quem não está recebendo leads
  ou não está usando o CRM (0 lead em 3 dias, WON, cards parados). ClickUp: tarefa "Internal dashboard: daily GHL audit".
