# Pauta — Pool Duck Wesley Chapel, follow-up quinta 19/11 15h (horário do Justin; Justin + Ed + Frank, Pedro se entrar)

Base: reunião de 16/11 (`docs/poolduck-wc-reuniao-2026-11-16.md`), V9 na conta desde 16/11 (log 16/11 e 17/11 em
`docs/execucao-2026-10-27-clearpool-dash.md`), respostas do guia do CRM do Justin aplicadas 17/11 e resposta mandada a
ele 17/11 (cc Ed/Frank).

## Se o Pedro entrar na reunião — o que já está pronto (30 s)
- Conta no V9 desde 16/11: pipeline **Pool Leads** (108 cards antigos já classificados: 6 Won Weekly, 21 Recurring, 4 Lost,
  1 In Communication, 76 New Lead para a equipe ligar), 14 fluxos do V9 publicados (ligação atendida/perdida, form do site,
  contato novo → Debbie, SMS recebido → Debbie, Quote Sent, No Response, No-Show, Lost, Recurring, Spam, SMS Reply,
  Reactivation ×2). Clientes antigos protegidos: `pre-snapshot` (2.675) e `existing customer` (1.243) — nada dispara para eles.
- As 4 linhas tocam o celular da Debbie (+1 352-806-9600). Duplicados e fluxos do Steve apagados (backup).
- Os 15 textos do Justin estão no ar palavra por palavra (guia do CRM); follow-ups só seg–sex 8h–17h; "Reply STOP to opt
  out" no 1º texto de chamada perdida; Terms of Service anexado ao e-mail de boas-vindas; boas-vindas próprias de
  reparo/obra.
- **Ainda em draft (precisa de decisão na call)**: Won Stage (boas-vindas com ToS), Review Request/Responses (NPS),
  Missed New Lead SMS (hoje sai o texto nativo da Debbie), appointments.

## Decidir na quinta
1. **Boas-vindas**: publicar o Won Stage do V9 (M10 e-mail com ToS + M11 SMS; reparo/obra) e pôr em draft o
   "*Welcome NEW Residential Client Messaging" deles (por tag `new residential client`)? Sem isso o ToS nunca sai.
   Atenção: o Won Stage dispara ao mover card para Won — combinar que a equipe passa a mover os cards.
2. **Review**: ligar o pedido de nota (NPS) + Review Request? Precisa: form de NPS na conta (eu crio, `pd_lwr_nps_gate.py`),
   custom value `nps_survey_link` e link de review do Google (custom value "Public Review Link" está vazio; conectar o
   Google na reputação ou eu monto o `writereview?placeid=`). Gate: nota 4–5 → Google; 1–3 → "what could we have done
   better?" + aviso à equipe; sem nota em 7 dias → sem link.
3. **Chamada perdida**: fica o texto nativo (o da Debbie, já com STOP) ou passa para o "Missed New Lead SMS" do V9 (com
   follow-ups)? Os dois juntos = 2 textos.
4. **Menu "aperte 1" contra spam** nas linhas: sim/não (hoje não tem; toca direto a Debbie).
5. **Quem recebe os avisos** além da Debbie (Justin? Preston?) e qual login fica nos usuários duplicados (2 Debbie, 2 Preston).
6. Fluxos próprios deles que seguem no ar (cartão/ACH, link do form de orçamento, media release, 7x7, Epperson, TAG
   Orchestrator, avisos de webchat/chat widget): manter todos? O cartão/ACH usa `pool_brain_customer_portal_link` —
   conferir que está preenchido com `poolduck.poolbrain.com`.
7. **Meta**: a conta de anúncio na integração é "Justin Denham", não "Pool Duck Wesley Chapel" — qual roda os anúncios da WC.
8. **LWR / Odessa**: mesma fase 2 (V9 + guardas + cards) depois desta call — OK do Ed para começar.

## Perguntar ao Justin
- Imagens para o e-mail de boas-vindas (ele perguntou; eu disse que sim) — pedir os arquivos.
- 2 possíveis erros de digitação dele (deixei como estão): M10 "the email address that we sent **the this** email to";
  M19 "- On the text message" (seria "On the way text message"?). Corrigir?
- A equipe está movendo os cards (New Lead → … → Won/Lost)? Sem isso Won Stage/Review/Google Ads não recebem sinal.
- Recebem os avisos no celular (app LeadConnector com notificações)? Debbie está atendendo as ligações das 4 linhas?
- Mensagens antigas sem resposta da reunião de 16/11 (Joni Hancock, Kathy Owen — cobrança, Saleena — Odessa, Michele —
  login do portal): foram tratadas?

## Depois da call (eu)
- Aplicar as decisões (GET + backup; nada dispara para contato antigo; fluxo novo publicado só com OK), `pp_call_check`,
  `pd_wc_guide_extras.py` se rodar `pp_wording --apply` de novo; atualizar `docs/TODO.md` (item C) e o log.
