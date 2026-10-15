# TODO — o que depende de você (atualizado 15/10/2026, noite)

Só entra aqui o que não deu para resolver daqui depois de tentar. Conferido ao vivo em 15/10.
Histórico e detalhes: `docs/execucao-2026-10-13.md`.

## Urgente

1. **Pool Keepers — a linha 805-262-9070 toca 1× e cai** (Frank). O encaminhamento para 805-457-8212
   está certo e não há IVR, mas a ligação **nem chega ao GHL** (nenhum registro, contato ou workflow).
   Os SMS da conta falhavam em 07/10 com "Trial mode not enabled for this agency" e o telefone usa
   Twilio rebilling. Conferir no painel: Pool Keepers → Settings → Phone System (aviso de trial,
   suspensão ou verificação) e Agency → Billing → carteira da Pool Keepers. Depois o Frank liga de
   novo e me passa hora + número de origem (a API não tem log de chamadas).
2. **Bluewater Brokerage (Bill Burch) — parte de GHL** (Frank/Val/Vikkar, 15/10). O GHL é **do Bill**,
   fora da nossa agência (não aparece nas 57 sub-contas). Pedir ao Bill: adicionar
   pedro@poolprofits.com como usuário **Admin** na conta dele (Settings → My Staff). Com acesso, monto:
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
6. **Orange Tree**: (a) chegou na sua caixa o e-mail de teste enviado **pela conta da Orange Tree**
   ("🚨 New Facebook lead: TEST lead email", 15/10)? Se sim, o cliente procura em Spam/Promoções;
   se não, problema no e-mail da sub-conta (Settings → Email Services). (b) Val/Frank reenviam o form
   com dados novos. (c) O celular do cliente (623) 974-5300 está com STOP desde 09/03 — só ele reverte
   (mandar START para o número da conta) se quiser os alertas por SMS.
7. **BluVantage**: na próxima submissão real, conferir que ela aparece na conversa do contato e que o
   e-mail chega para Vanessa e Paul.
8. **Review gate (NPS)**: na Test Snapshot, abrir o link do NPS de um contato de teste, responder 5 e
   ver o campo NPS Score ficar 5 (captcha impede automatizar).

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
12. **Tag da linha GBP nas outras contas**: na Pool Shack já marca `website & gbp`; para as demais (e o
    master), `pp_line_tag.py --only "<conta>" --apply`.
13. **Passion — forms "PPC - Home Quote" / "PPC - Universal Quote"**: estão no site orgânico (home e
    todas as páginas internas) e foram para o Website Form Fill (sem tag/conversão de Ads). Se esse site
    também for destino de anúncio, dizer — aí entra a parte de Ads.
14. **Dois telefones nas mensagens da Southern**: `business_phone` (214-308-1744) vs
    `a2p_verification_number` (214-922-1914, agora o número do IVR). Escolher um padrão.
15. **Paid Ads na Bahama, Passion e Pool Shack**: se não rodam Ads para a landing `go.*`, pôr os 08 Paid
    Ads em draft e rodar `pp_forms.py`. Na Pool Shack o AdWords Form escuta um form que não existe mais.
16. **A2P da Stay Fresh e da Pool Keepers**: conferir em Settings → Phone System → Trust Center.
17. **Stay Fresh**: draft "Pool Smart OC Customers - SMS" (nome de outro cliente) revisar/apagar;
    "Ryan Quitler" → **Quilter**? (aguardando o Frank).
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

## Concluído desde a versão anterior (14 → 15/10)

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
