# TODO — o que depende de você (atualizado 16/10/2026, fim do dia)

Só entra aqui o que não deu para resolver daqui depois de tentar. Conferido ao vivo em 16/10.
Histórico e detalhes: `docs/execucao-2026-10-13.md`.

## Urgente

1. **Pool Keepers — a linha 805-262-9070 não funciona** (Frank 15 e 16/10; você também testou em 16/10:
   nem conecta). Encaminhamento para 805-457-8212 certo, sem IVR, igual à Pool Shack (que funciona);
   nenhuma ligação chega ao GHL → problema no serviço de telefone da sub-conta. **Você vai abrir chamado
   no suporte** (número, horários dos testes, e que em 07/10 os SMS da conta falhavam com "Trial mode not
   enabled for this agency"; telefone com rebilling). Resolvido → Frank liga de novo e eu confiro o registro.
1b. **Stay Fresh — campanha de SMS "drain & wash" (Frank/Mike)**: pronta em **rascunho**, nada enviado
   (`pp_sms_campaign.py`): "Drain & Wash Campaign - Active Clients" com o **texto do Mike exatamente como
   veio** (sem nenhuma alteração; 8 segmentos por SMS) e "… - Replies" (resposta → tag `drain wash
   interested` + SMS e e-mail para o Mike). Público: 105 `active client` com telefone, nenhum DND. A2P
   aprovado (você confirmou). **Falta só dia/hora** do envio → eu rodo `launch --confirm`.
2. **Bluewater Brokerage (Bill Burch) — parte de GHL** (Frank/Val/Vikkar, 15/10). **Perguntar onde fica o
   GHL do Bill**: não está nas 57 sub-contas da Pool Profits nem nas 10 da Pool Duck. Pista: a agência
   Pool Duck é da **Sharon Burch** (sharon@poolduck.com) e o Bill cita "os arquivos do Canva da Sharon"
   → pode ser conta própria dele ou ligada à Sharon. Pedir: o endereço em que ele entra no GHL
   (app.gohighlevel.com ou um white-label), o Location ID (Settings → Business Profile) e
   pedro@poolprofits.com como usuário **Admin** (Settings → My Staff). Com acesso, monto:
   - 3 webhooks de entrada (calculadora, Seller's Guide, Buyer's Guide) → contato com tags (`route
     calculator` / `seller guide` + `opinion of value requested` / `buyer registration`, `call requested`
     quando pedir ligação), card no pipeline, e-mail para o Bill com tudo; o Vikkar troca o envio do
     site (hoje só e-mail para o Bill) pelas URLs;
   - SMS de confirmação só com o checkbox marcado (precisa de número com A2P na conta dele);
   - link do calendário do GHL dele no lugar do Calendly (o Bill disse que manda o link).
   Respeitar a promessa da calculadora: "we will not call you unless you ask us to" (nada de follow-up
   automático além da confirmação).
3. **Trocar os dois refresh tokens colados no chat**: Pool Profits e Pool Duck. Logout no GHL e gerar
   outro com `docs/get-firebase-token.md` (o da Pool Duck está num arquivo de env fora do repo).

## Testes que só você (ou a equipe) consegue fazer

4. **IVR da Southern**: ligar para (214) 922-1914 — 1 → celular do Brett (214) 893-2315; 2 →
   (214) 308-1744; ninguém atende → caixa postal + SMS "sorry we missed your call". Nenhuma ligação
   desde que entrou no ar, mas a conta recebe poucas (últimas: 09/10, 01/10, 30/09).
5. **Sunwave (Val)**: reenviar o form da landing go.sunwavepoolpros.com/sunwave-weekly e ver as tags
   `new lead`, `new form fill`, `adwords` + card + SMS para os Connolly. Vale avisar que 3 envios do
   "Service Page - Contact Form" de setembro (Velva Coffey 05/09, Divanshi Gupta 2× 17/09) nunca viraram
   card — esse form agora vai para o pipeline.
6. **Orange Tree**: (a) e-mails de lead agora vão também para **vanessa.orangetreepools@gmail.com** (é
   ela quem lê) e cada **SMS de cliente** chega por e-mail com os links das fotos; conferir no próximo
   lead/resposta real. (b) Fotos: as 2 linhas aceitam MMS e as fotos chegam no GHL (ex.: 21/09, 3 fotos
   do Nathaniel Lopez na conversa); o aviso por SMS não leva foto (só link) e o celular (623) 974-5300
   está com **STOP desde 09/03** — para voltar a receber os avisos por SMS, a Vanessa manda START para
   623-343-0400 e 623-244-8621. Melhor ainda: app LeadConnector no celular (mostra as fotos + push).
   (c) Conferir se chegou na sua caixa o teste enviado pela conta da Orange Tree em 15/10.
7. **BluVantage**: na próxima submissão real, conferir que ela aparece na conversa do contato e que o
   e-mail chega para Vanessa e Paul.
8. **Review gate (NPS)**: na Test Snapshot, abrir o link do NPS de um contato de teste, responder 5 e
   ver o campo NPS Score ficar 5 (captcha impede automatizar).

9a. **Southern (Val, 16/10)**: a landing de limpeza usa o novo **GOOGLE ADS - FORM** — se o builder
    da página estiver aberto, **recarregar antes de salvar** (senão volta o form antigo). Val instala a
    conversão em https://service.southernpoolandoutdoors.com/ty-page-2934-3692 e testa form + ligação
    no 972-632-3259. A landing de reforma (remodeling.…) segue com o "Appointment Booking Form", agora
    ligado ao pipeline como lead do site — se ela também for de Google Ads, dizer.
9b. **Sunwave**: avisar a Val que sunwavepoolpros.com redireciona para **sunwavepros.com, que não existe**
    (www abre página vazia) — se esse endereço estiver em anúncio/GBP, está quebrado. No Zap do Google
    Ads Lead Form, trocar a tag/origem "website form fill" por algo próprio (hoje um workflow repõe
    `google ads lead form`).

## Decisões

9. **Snapshot "daqui pra frente"** (pergunta do Frank): o master **Snapshot Pool Profits** já está sem o
   "free month", mas tem só 1 etapa Won e os bugs antigos (merge fields, tarefas sem responsável/1970,
   links de calendário, "Clear Pool Solutions Tucson", notificação sem usuário). Você libera eu corrigir
   (`pp_mirror` + `pp_fix` + `pp_won_stage`) e depois dá **Agency → Account Snapshots → Refresh**
   (a API não deixa).
10. **BluVantage — bloquear spam no telefone**: passo no começo do IVR deles que desliga para contato com
    tag `spam`. Mexe em toda ligação → só com OK do cliente e ligação de teste junto.
11. **Sunwave — ligações do anúncio**: a landing mostra 407-864-6909 (linha "Adwords"), que passa pelo
    "Marketing - IVR" deles e só ganha `new lead`/`inbound call`. Publicar o "AdWords Call In - New
    Lead" com esse número dá `adwords` + conversão, mas também manda SMS ao lead 5 min depois.
12. **Tag da linha nas outras contas**: Pool Shack e Southern já marcam `website & gbp` (Southern também
    `facebook` na linha Facebook Ads); para as demais (e o master), `pp_line_tag.py --only "<conta>"
    [--line facebook --tag facebook --name "Facebook Ads Call - Tag"] --apply`.
13. **Passion — forms "PPC - Home Quote" / "PPC - Universal Quote"**: estão no site orgânico (home e
    todas as páginas internas) e foram para o Website Form Fill (sem tag/conversão de Ads). Se esse site
    também for destino de anúncio, dizer — aí entra a parte de Ads.
14. **Dois telefones nas mensagens da Southern** (mesma questão do Frank na Pool Shack): `business_phone`
    (214-308-1744, destino do encaminhamento, **não rastreado**) vs `a2p_verification_number`
    (214-922-1914, linha do IVR, rastreada). Na Pool Shack os SMS passaram a usar só a linha rastreada;
    fazer o mesmo na Southern e nas outras? (`pp_snippet_replace.py`).
15. **Paid Ads na Bahama, Passion e Pool Shack**: se não rodam Ads para a landing `go.*`, pôr os 08 Paid
    Ads em draft e rodar `pp_forms.py`. Na Pool Shack o AdWords Form escuta um form que não existe mais.
16. **A2P da Pool Keepers**: Settings → Phone System → Trust Center (o da Stay Fresh está aprovado).
17. **Stay Fresh — drafts antigos**: "AdWords Tracking", "AdWords Tracking - Calls" e "Won Customer"
    apontam para uma etapa de pipeline que não existe mais (desligados) — posso apagar. Draft "Pool Smart
    OC Customers - SMS" (nome de outro cliente) revisar/apagar.
18. **"Sequential Call Routing" do snapshot**: é o IVR da BluVantage copiado (toca Vanessa/Fred/Paul);
    publicado em Southern, Passion, Bahama, Pool Shack e no master, mas não dispara (números são da
    BluVantage). Apagar das outras contas e do master.
19. **Kari (Southern)**: em 🏆 Won - Weekly. Se foi reparo/instalação, arrastar para o Won certo.

## Manual no GHL (sem API)

20. **Reputation → Settings → e-mail de review**: conferir o logo nas contas antigas.
21. **Sites com WPForms** (Pool Shack, Bahama, Pool Keepers): quando trocarem por form do GHL, rodar
    `pp_forms.py --only "<conta>" --apply` (agora reconhece também forms "… Quote").

## Pool Duck (outra agência) — detalhes em `docs/poolduck-lakewood-ranch.md`

22. **Campanha de review (Lakewood Ranch)**: pronta e testada, aguardando o cliente aprovar os textos →
    `pd_lwr_reviews.py launch` (274 clientes `turtle rock`, 37 excluídos). Confirmar os 2 McQuaid.
23. **Landing pages LWR**: teste manual do form (captcha); números de rastreamento (cliente vai
    comprar); IDs de Ads/GTM/Pixel; Trustindex do LWR; confirmar áreas/horários; apagar os 2 contatos
    "TEST - Pool Duck setup".
24. **Avisar**: alertas antigos do LWR ("… - Steve") sem destinatário; popup do WC com form de outra
    empresa ("Poolfessionals AdWords").

## Concluído desde a versão anterior (16/10)

- **Southern** (Val): landing de limpeza com o novo **GOOGLE ADS - FORM** (obrigado próprio, código do
  país, endereço com busca); AdWords Form e AdWords Call In publicados com tags, SMS e e-mail para o
  Brett; tag por linha (`facebook`, `website & gbp`); form da landing de reforma ligado ao pipeline.
- **Sunwave**: leads do Google Ads Lead Form (via Zapier) ganham `google ads lead form` (8 já marcados).
- **Pool Shack** (Frank): todos os SMS automáticos agora mostram a **linha rastreada** 480-428-0655 (10
  templates; antes 5 usavam o celular 480-798-2888, fora do rastreamento).
- **Stay Fresh**: "Ryan Quitler" → **Quilter**; campanha de SMS montada em rascunho (item 1b).
- **Erros de tag no construtor** (Frank viu no Won Stage da Stay Fresh): as tags novas do Won Stage
  (`won weekly`, `won repairs and installs`, `won construction`) e outras do snapshot (`do not
  remarket`, `review received`, `high priority`…) eram usadas sem existir na conta. Criadas em 10 contas
  + master (`pp_tags_missing.py`); nenhuma tag usada sem existir.
- **Orange Tree** (Vanessa): e-mail de lead também para vanessa.orangetreepools@; SMS de cliente por
  e-mail (com links das fotos) para ela e para orangetreepools@.

## Concluído antes (14 → 15/10)

- **Passion**: o site agora usa forms do GHL (o webhook para a conta de fora sumiu — antigo item urgente
  resolvido pelo site). Os 2 forms novos não iam para lugar nenhum; ligados ao Website Form Fill
  (nenhum lead perdido: 0 envios até agora).
- **Forms de lead sem rota** ligados ao Website Form Fill: Sunwave, Orange Tree e BluVantage
  (`pp_forms.py`). Sunwave: SMS de lead novo do site estava sem destinatário → Connolly.
- **BluVantage**: texto NEW LEAD só nos forms (ligação/SMS não, a pedido do Paul); spam/clientes fora
  dos cards; forms por e-mail para Vanessa e Paul com todos os campos (teste ok); submissão na conversa;
  Chris Kelleher marcado para 21/10.
- **Orange Tree**: e-mail de lead para o cliente (Facebook, site, chat); tag/card antes das notificações.
- **Sunwave**: AdWords Form escuta o "Google ADS - FORM" da landing; alerta para os Connolly.
- **Pool Shack**: tag `website & gbp` nas ligações da linha principal.
- Antes: "free month" fora das 16 contas; Won Stage nas 3 etapas Won; IVR da Southern; Labs; duplicatas
  apagadas; lista da Stay Fresh importada.

Obs.: a marcação "incompleto" que o GHL mostra nos passos "Add Task" é só visual — as tarefas são
criadas e atribuídas.
