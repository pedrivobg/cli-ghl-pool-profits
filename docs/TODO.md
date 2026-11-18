# TODO do Pedro — só o aberto (16/11/2026, revisão geral do ClickUp)

Curto de propósito (as rotinas leem este arquivo). **Regra das tarefas do ClickUp (Pedro 10/11)**: toda tarefa que eu crio
tem prazo realista e é fechada quando o meu trabalho está feito e testado; se só falta teste real do Pedro, comento, fecho
e acrescento o teste no checklist da tarefa única "Live tests with Pedro" (`86bd1b3b5`); se depende de outra pessoa,
comento quem/o quê e ajusto o prazo — nada fica vencido sem dono. Uma linha por item; detalhe e histórico em
`docs/execucao-*.md` e `docs/TODO-arquivo-2026-11-04.md`. Item fechado sai daqui. Teste que avisa cliente:
combinar antes.

## Regras da rotina (lidas a cada disparo; Pedro 11/11)
- **Memória de cada rodada é obrigatória** (Pedro 18/11: "se não fica repetindo"; a revisão da noite de 17/11 listou
  como pendente o que já estava feito — Bonneville, Justin da Pool Duck — porque a rodada da manhã não gravou nada). Toda
  rodada, mesmo sem código: (1) tira daqui o que fechou e atualiza a linha do que mudou; (2) acrescenta 2–5 linhas no log
  `docs/execucao-2026-10-27-clearpool-dash.md` (o que fiz, onde postei, o que espera quem); (3) commit + push antes de
  terminar. Antes de pôr um item no e-mail do Pedro: conferir este TODO, o fim do log, o ledger e a pasta Enviados
  (`subject:(Aprovar OR "Passo seu") newer_than:3d`) — item já respondido/feito não volta.
- **Marcar como lido no ClickUp é obrigatório** (Pedro 17/11: "está ficando uma bagunça"). Depois de responder/resolver um
  item do ClickUp: `python3 scripts/cu_mark_read.py --channel <canal/DM> --thread <parent do thread> --task <task>` (ids
  vêm do payload: `cu-chat-<msg>` + `parent=`, `task=`; o canal sai da url `/chat/r/<canal>`). Marca DM/canal, thread e
  comentários como lidos e tira a tarefa do Inbox (read + clear). **No fim de toda rodada: `python3 scripts/cu_mark_read.py
  --sweep`** (marca lido tudo em que o Pedro escreveu por último, um "thanks" depois do Pedro ou conversa entre outros; lista
  LEFT o que ainda precisa de resposta). O n8n também manda essa linha em todo disparo (18/11).
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
- **Assunto de Google Ads/Meta (configuração, dados) = Val responde** (Pedro 18/11, Sunwave): eu só respondo a parte do CRM.
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
(Revisto 18/11 14h UTC contra ledger, Gmail e estado ao vivo. Saíram por já estarem feitos: número Google Ads da Bonneville
— linha +1 385-503-7952 → Justin desde 16/11; SMS de teste da Sparkling — feito 18/11; resposta ao Justin — enviada 17/11
21:27 UTC; Refresh do snapshot — feito 18/11; teste das 2 linhas da WP Pools — feito 17/11; plano Pool Duck — WC migrada 16/11.)
1. **Testes reais** (ClickUp [Live tests with Pedro](https://app.clickup.com/t/86bd1b3b5), prazo 21/11): inclui a chamada
   perdida da Blue Lagoon (ligar para +1 480-400-0140 fora do horário da Destiny e deixar cair; Pedro 18/11: "mais tarde").
2. **Pool Keepers – call com o Nathan**: proposta qui 19/11 **10h PT** (= 15h BRT) postada no Basecamp 18/11 14:04 UTC; quando o
   Nathan confirmar, o Pedro manda o convite/link da reunião (ou me passa o link e eu posto).
3. **Pool Duck WC – follow-up qui 19/11 15h** (Justin/Ed/Frank): pauta em `docs/poolduck-wc-reuniao-2026-11-19.md`.
4. (opcional, desde 10/11) **API do Claude no n8n**: credenciais "Anthropic Pool Profits" e "GHL Agency Token" → agente do n8n
   para itens fáceis do inbox. Só se o Pedro quiser.
Contexto que NÃO é passo do Pedro (não pôr no e-mail): West Coast A2P espera o endereço do EIN letter (Frank, `86bd3m8c9`);
contas novas esperam o 1º número (Frank); gate de nota = 4 ou 5 (feito 17/11); sem nota em 7 dias = sem link (feito 16/11);
contas antigas para ver com o time e Pool Duck LWR/Odessa (fase 2 depois de quinta); Reign LPs = lado GHL meu (`86bd2jrc6`).

## Esperando outros
- Frank (18/11, `86bd4tugh`): confirmar com a Vanessa (BluVantage) se o card pode ir sozinho de New Lead para In
  Communication em ligação/SMS (a etapa dispara e-mails de nurture) — pedido da Val.
- Val (18/11, Pedro passou para ela; pedido na `86bd4kucg`): selecionar a conta Google Ads 880-434-4425 na LWR → `GHL_AGENCY=poolduck pp_won_ads.py apply --only MosKIX4oux96vchwHZ5W` e avisar a Val (`86bd4kucg`).
- Frank (17/11): Passion — desligar também "Website Webhook Lead To Pipeline"? (19 em draft, lista em reports/); WP Pools —
  3ª linha (Facebook)?; Service Agreement Example na West Coast (ofereci colocar).
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
