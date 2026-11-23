# TODO do Pedro — só o aberto (16/11/2026, revisão geral do ClickUp)

Curto de propósito (as rotinas leem este arquivo). **Regra das tarefas do ClickUp (Pedro 10/11)**: toda tarefa que eu crio
tem prazo realista e é fechada quando o meu trabalho está feito e testado; se só falta teste real do Pedro, comento, fecho
e acrescento o teste no checklist da tarefa única "Live tests with Pedro" (`86bd1b3b5`); se depende de outra pessoa,
comento quem/o quê e ajusto o prazo — nada fica vencido sem dono. Uma linha por item; detalhe e histórico em
`docs/execucao-*.md` e `docs/TODO-arquivo-2026-11-04.md`. Item fechado sai daqui. Teste que avisa cliente:
combinar antes.

## Aberto hoje
- 18/11: Success Team + Ed (automação de SEO): propus tratar na mid-week de hoje 16h BRT (1 PM CT); levar ideias.
- 20/11: Clear Pool LPs novas (`86bc6vvha`, Val): forms Weekly `ZxZ4nQ9f…` / Repairs `UgAUSMUp…` (+ Service Needed) no gatilho do
  AdWords Form - New Lead + fluxos de tag feitos (`scripts/cp_lp_launch.py`). Esperando Atif (páginas + 2 URLs de obrigado →
  `apply --thanks-weekly/--thanks-repairs`) → testar envio em cada página. Conversão: só "Converted Lead - WON" (Val 23/11; Won -> Google Ads conferido).
- 19/11: Bonneville Ads (`86bcwer98`, Val): fluxos publicados; lead form mapeado + Active; ligação e SMS reais conferidos e
  apagados. Send Data não existe mais no Google Ads (Val) → campanha ativa; validar no 1º lead real (contato/tags/card/avisos) e confirmar à Val.

## Regras da rotina (lidas a cada disparo; Pedro 11/11)
- **Google Ads do cliente = sempre a Val** (Pedro 19/11: ele não tem acesso). Nunca pedir ao Pedro passo dentro do Google Ads
  (Send Data, conversões, URLs): pedir à Val no ClickUp. Ao Pedro só o lado do CRM (tela do GHL, ligação/SMS de teste).
- **Resposta ao Pedro no thread dele fica NÃO LIDA** (Pedro 18/11: a rotina responde no thread do [Passo seu]/[Aprovar], mas
  marca como lido e ele não vê). Ao responder ao Pedro: depois de enviar, marcar a SUA resposta como não lida
  (Gmail `label_message` messageId=<id da resposta> labelIds ["UNREAD"]). "Marcar o thread como lido" vale só para
  e-mails de outras pessoas já tratados — nunca para um thread em que a última mensagem é uma resposta minha ao Pedro.
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

- **Regra – Basecamp: post novo visível ao cliente** (Pedro 23/11): o conector cria post/mensagem só para o time e o `set_client_visibility` pede confirmação humana (trava em rotina). Depois de criar o post, chamar o webhook n8n "Basecamp - tornar visivel ao cliente" (`PkZYrNmhEMVNvltr`): `curl -sS -X POST https://n8n.valenteai.cloud/webhook/bc-visible-7f3c9a2e4b1d48e6a0c5 -H "Content-Type: application/json" -d '{"bucket_id":<projeto>,"recording_id":<post>}'` → `{"ok":true,"visible_to_clients":true}` (`"visible":false` esconde). Usa a credencial OAuth2 "Basecamp OAuth" do n8n (app 37signals "Pool Profits Automation"); falha → e-mail "[URGENTE] Basecamp" ao Pedro (401 = Reconnect na credencial). Comentário em post que o cliente já vê herda a visibilidade: não precisa.

## Você faz
(Revisto 18/11 14h UTC contra ledger, Gmail e estado ao vivo. Saíram por já estarem feitos: número Google Ads da Bonneville
— linha +1 385-503-7952 → Justin desde 16/11; SMS de teste da Sparkling — feito 18/11; resposta ao Justin — enviada 17/11
21:27 UTC; Refresh do snapshot — feito 18/11; teste das 2 linhas da WP Pools — feito 17/11; plano Pool Duck — WC migrada 16/11.)
1. **Testes reais** (ClickUp [Live tests with Pedro](https://app.clickup.com/t/86bd1b3b5)): Blue Lagoon dispensado 23/11 (ligações reais
   já provaram o CRM; espera a Destiny). Sparkling feito 23/11.
3b. **Sparkling – Lead Form**: filtro `adAccountId` tirado 19/11; Send Data não existe com o app novo → validação = 1º lead
   real (eu confiro). GA da Sparkling na propriedade da agência → propriedade própria (86bd4kucg). Nada do Pedro.
(Reign: envio real feito pelo Pedro 18/11 21:41 UTC; conferido 19/11 — card New Lead, tags de serviço/ZIP, aviso ao Stephen
entregue com ZIP 92881, SMS de obrigado; teste apagado.)
(Pool Duck WC – follow-up 19/11 feito: Won Stage + Review Request aprovados/publicados; aviso de lead novo ao Justin em
todas as origens e lista do PoolBrain importada no mesmo dia — ver execução 19/11. Matt/Odessa e verba de baixa
temporada = Ed/Jonathan; encontro presencial 29–31/01.)
4. (opcional, desde 10/11) **API do Claude no n8n**: credenciais "Anthropic Pool Profits" e "GHL Agency Token" → agente do n8n
   para itens fáceis do inbox. Só se o Pedro quiser.
Contexto que NÃO é passo do Pedro (não pôr no e-mail): West Coast A2P espera o endereço do EIN letter (Frank, `86bd3m8c9`);
contas novas esperam o 1º número (Frank); gate de nota = 4 ou 5 (feito 17/11); sem nota em 7 dias = sem link (feito 16/11);
contas antigas para ver com o time e Pool Duck LWR/Odessa (fase 2 depois de quinta); Reign LPs: CRM ligado 18/11 (`rg_lp_launch.py`); Val responde conversão (só "Converted Lead - WON") e número de ligação das LPs.

4. **Blue Lagoon – ligações não chegam no celular**: Destiny 20/11 17:56: celular 602-400-7289 (dela) sem filtro, mas nem registra
   as ligações (McCabe 11:03, Zaremba 19:16 AZ); CRM encaminhou as duas → caixa postal do CRM. Hipótese: filtro da operadora ou
   linha 602 encaminhando para a IA "Mae". Pergunta postada no Basecamp "IVR/Spam Calls" 20/11 19:01 UTC (aprovada) → esperando
   a Destiny (operadora + lista de bloqueados, setup da Mae). IVR SPAM Detection segue em draft; "Missed New Lead" em draft.
5. **Sparkling – Lead Form**: com o app "Google Lead Ads" (sincroniza pela API) o Google Ads não mostra "Send test data" (só
   existe para entrega por webhook). Validação = 1º lead real; eu confiro e aviso. Não é passo do Pedro.

## Esperando outros
- BluVantage (Frank 20/11): etapa "🤝 Vendors" criada; Vanessa escolhe entre Booked Assessment (14 cards) e Scheduled (0) —
  nenhuma dispara nada. Se ela quiser só uma: mover cards/apagar a outra (sem gatilho publicado).
- Streamline Results (`86bd5qkpc`): sem sub-conta (questionário não respondido) → rodada diária.
- **Pool Palooza (20/11)**: "Lead Source - Tag (forms & bookings)" publicado; conferir no 1º lead real de Free Trial/F1/agendamento
  que os campos "Lead Session Source"/"Lead GCLID" vieram preenchidos e a tag bate (adwords/facebook/organic/direct).
- **Check-ins 20/11** (Southern, Stay Fresh, YardSpring): só visíveis ao time; links mandados ao Pedro 23/11 (thread revisão da noite 20/11) para ele deixar visível.
- **Justin (Pool Duck WC, call 19/11): imagens para o e-mail de boas-vindas (M10)** — quando chegarem (Basecamp/e-mail/ClickUp;
  baixar onde vier): subir na mídia da WC (`GHL_AGENCY=poolduck`, location uJr8H2qaQM5ffZxeYFqn), pôr no e-mail M10 do
  "Won Stage" (publicado 19/11; editar o passo **e** o template; manter o Terms of Service e o link do portal) via
  `config/pool_duck_wc_wording.json` + `scripts/pd_wc_guide_extras.py`, testar com ZZ TEST (e-mail do Pedro) e confirmar ao Justin.
- Pool Duck (20/11): East Orlando (Luis, `m2glhRgphyM7uXh4Rc8u`): Sharon carregou o V9; custom values, missed-call nativo off,
  dono/avisos = Luis feitos; "add owner" consertado pelo Pedro 20/11 13:27 e conferido (Luis). Falta:
  domínio + privacy/terms (A2P), Google review link, preços. Ed pediu o A2P de (689) 350-4006 (20/11): perfil ok, falta website →
  site no ar = `GHL_AGENCY=poolduck pp_a2p.py campaign/submit -n "East Orlando"` no mesmo dia; perguntei ao Ed se encaminha
  para o Luis (321) 948-6198 (hoje sem encaminhamento). Westchase (`IzfAqV2fqR1mEHAPVglZ`): V9 fase 1 em draft (20/11);
  publicar quando houver número/avisos da Christine e endereço de A2P (Ed). Cibele: Sharon cria com o V9 e avisa.
  Snapshot V9 da agência Pool Duck ainda traz "Reply in the GHL app" no Notify Owner (corrigir nas contas novas).
- Pool Keepers/Skimmer: call com o Nathan feita 19/11; esperando ele trocar Location ID/chave no Skimmer → conferir a conexão na
  KjLd e tirar a chave antiga da hh6X9 (tarefa 86bd02rg9, prazo 24/11).
- Paul (BluVantage, via Frank 19/11): "por que recebo isso a cada SMS?" = aviso "Inbound SMS - Notify Owner" (pedido do Ed 13/11).
  Texto "GHL app" → "Pool Profits app" em todas as contas (20/11). Esperando o Frank/Paul: manter, desligar ou mandar a outra pessoa.
- Shane (Wrigley's, 19/11): pediu ideias para mais ligações; Ed propôs campanha SMS/e-mail (reativação/promo) + reviews.
  Se o Shane topar: monto a campanha em draft e mando o texto para aprovação.
- Frank/cliente (19/11): Puddle Jumper — quem da lista importada é cliente ativo (tag `active client`); Frank perguntou ao cliente.
- Passion (20/11): form do site agora avisa por SMS o escritório +1 615-624-7624 (John deu STOP no celular dele em 18/11); conferir no próximo lead do form. "Inbound SMS - Notify Owner" vai ao John (DND) e ao Brad (20/11).
- Val/Atif (19/11, `86bc6vqr9`): LP nova da Passion (ChatGPT Ads). Quando o link vier: ligar o form ao CRM com os avisos
  (SMS 615-624-7624 + passionpoolcare@gmail.com) e tracking, testar ponta a ponta e responder na tarefa.
- Success Team/Ed (18/11): call sobre automatizar tarefas de SEO — eles retomam amanhã (19/11); pedi a lista das tarefas por
  escrito no thread do canal Pool Profits para eu me preparar (ideias do que dá para automatizar).
- Val (18/11, `86bd4tugh`): confirma com a Vanessa (BluVantage) em 19/11 se o card pode ir sozinho de New Lead para In
  Communication em ligação/SMS (a etapa dispara e-mails de nurture). Quando disser sim: ligar e testar no mesmo dia.
- WP Pools A2P (Frank 20/11: sem 3ª linha, A2P com (616) 879-8101; `LINE_CAP` no pp_new_account): falta go.wppools.com
  (GoDaddy, CNAME go → sites.ludicrous.cloud pelo cliente + Frank liga ao site "New A2P Verification") → a rodada diária envia.
- West Coast: Frank decide se apago os 2 "Pool Service Agreement" do Ed (17/11, texto ainda diz "Clean Co"); o Example está lá.
- Pool Keepers/Skimmer (17/11): a certa é a KjLd (BurchTech); Pedro criou a chave, Location ID + chave novos mandados ao
  Nathan por e-mail e Basecamp pedindo dia/hora da call. Esperando o Nathan trocar no Skimmer → conferir a conexão na KjLd
  e tirar a chave antiga da hh6X9 (Private Integrations, tela).
- Pedro (13/11): Pools of Perfection criada pela API; resposta ao Nathan (Skimmer nativo) e reunião de segunda aprovadas →
  extensão (prompt 2) posta; OK para pôr em draft as 2 cópias extras de Website Form Fill/Review Request da Clear Conceptz.
- Frank (12/11 noite): se o Brett apaga cards de lead da Southern (2 leads do Google Ads sem card, `86bd2t1kt`, 17/11) — Frank liga ao cliente (20/11).
  Padrão Skimmer para clientes mandado a ele (Enterprise = API; outros = Zapier só Skimmer→GHL; form do GHL fica no site).
- Felipe (Poolheads, via Frank): histórico como nota?, webhook "LVB - Meta Service" (único que falta antes de cancelar a conta antiga; 5 e-mails + 9 SMS conferidos na nova 17/11 com o token do ambiente), George como 2º toque 25 s/20 s (Frank pediu no Basecamp 16/11)
  (nome/e-mail/celular), página de privacidade, lista de clientes; Skimmer add-on → aí crio o token (Private Integrations,
  tela) e mando ao Felipe com o Location ID. Review Request da Poolheads fica draft (reviews no Skimmer). Calendário Leak
  Detection pronto e inativo: ligar na virada.
- GBP posts: Frank conecta os outros GBPs no Social Planner (`86bd1xdbu`, 24/11).
- Frank (16/11): Pool Smart OC ainda é cliente? (fora da lista de inativos até ele confirmar; Ads precisa reconectar, `86bd1zk8p`) — Frank liga ao cliente (20/11).
- Bonneville (ativa 19/11, anúncios em revisão): Val avisa no 1º lead; conversão de form fill (se quiser) e URL nova da Weekly
  (/weekly-pool-hot-tub-service) nos anúncios.
- Atif: páginas/obrigado de Poolheads, Pool Shack, YardSpring, BluVantage; tirar o número antigo da página Weekly da NorTex.
- Val: Google Ads conectado (Poolheads, Pool Shack, YardSpring) e acesso para o Send Data dos Google Lead Forms.
- Frank: Stay Fresh (avisos de ligação para o Kris, re-entry, IVR, lista de inativos); Pool Shack (retorno do Rob);
  tags universais; Pool Keepers (o que liga); GBP da Clear Pool no número de rastreamento.
- Frank (12/11): OK para o filtro de spam do form da Passion (telefone sem +1 / palavras de venda → spam, sem aviso; telefone só EUA)
  — 6 de 8 submissões em 30 dias eram spam.
- Derek (Clear Pool): publicar Review Request?, chave do Pool Brain. Erik (Ekahi) e Jeremy (SwimReady): ajustes por código.

## Em breve (combinado)
- **Ligações e SMS de todo cliente** (Ed 13/11, `86bd349d8`): depois do teste, `pp_sms_alert.py apply --all` (+ `pp_tags_missing`); dono das contas sem usuário com telefone (Stay Fresh, Blue Lagoon, Ponchos…) → Frank; linhas com IVR em draft (Dream Pools, Ponchos, Precision) → proposta ao Pedro antes de mudar encaminhamento. Linhas que só tocam no app (Aqua Clear, Clean Co, GID, Pool Palooza, Pool Keepers, Wrigley's) ficam assim (Pedro 17/11: decisão dos clientes).
- **Monitor de leads** (Frank/Val, Ed aprovou 13/11, `86bd349dt`, 18/11): alerta de card parado 3/4/5 dias + resumo a cada 3 dias dos clientes de Google Ads (tudo interno). 1º resumo no thread no começo da semana.
- **Dashboard interno** (Val, 06/11 e 09/11): auditoria diária de todas as sub-contas para prever erros (alertas/tarefas
  sem usuário, linhas sem encaminhamento, SMS falhando, gatilhos quebrados) e acompanhar quem não está recebendo leads
  ou não está usando o CRM (0 lead em 3 dias, WON, cards parados). ClickUp: tarefa "Internal dashboard: daily GHL audit".

- **Basecamp OAuth (23/11)**: conferir ~07/12 (1º vencimento do token, 2 semanas) que o webhook `bc-visible` ainda responde ok
  (o refresh da 37signals no OAuth2 genérico do n8n não foi testado). Se der 401: Pedro clica Reconnect na credencial.
