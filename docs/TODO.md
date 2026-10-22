# TODO do Pedro — só o que depende de você e ainda está aberto (21/10/2026, noite)

O que já foi feito está em `docs/execucao-2026-10-13.md`. Testes são nossos: nada aqui vai para a equipe ou
para o cliente testar.

## Mandar (textos prontos no chat de 21/10)

- **Frank — Pool Keepers**: decisões para publicar (mensagem de 21/10, noite).
- **Bluewater**: comentário no ClickUp "GHL Form Mapping" e resposta na thread do Vik (Vik, Ed, Frank, Val).
- **Frank — Pool Shack** (mudanças do Rob), **Frank + Ed — IVR da Stay Fresh**, **Frank + Ed — lista de inativos da
  Stay Fresh**, **Frank + Ed — tags universais**.
- **Val — LWR**: "Done, reminder Monday 10 AM" + passos do Google Business Profile.
- **Val — Google lead form** (4 contas): workflows prontos; resposta no chat de 22/10.
- **Vanessa (BluVantage)**: usuários da GoTour criados (texto de primeiro acesso).
- **Poolheads**: resposta sobre a portabilidade (pedir o e-mail do Jorge Arias).

## Contas novas (Poolheads, Rosebrook, Cleverblu) — faltam só coisas de UI

1. **Encaminhamento** (Settings → Phone Numbers → número → Edit → *Forward calls to*): Cleverblu **689-229-3738 →
   +1 407-922-8947**. Poolheads 936-301-4150 só até a portabilidade (depois o IVR cobre; item 5).
2. **Ligação de teste** em cada uma, sem atender: SMS de chamada perdida no seu celular + card em New Lead. Me avisa.
3. **A2P** dos números (Settings → Phone System → Trust Center): sem aprovação o SMS não sai.
4. **Rosebrook**: comprar um número ("Website & GBP") + A2P; link de review do Google (Lynsey, ou conectar o Google
   Business Profile em Settings → Integrations). O Review Request fica em draft até ter o link.
5. **Poolheads — portabilidade do 936-314-9255** (conta GHL antiga → nossa). IVR e resposta fora do horário prontos em
   draft (`scripts/pp_poolheads_port.py`).
   - **Antes**: e-mail do **Jorge Arias** (crio o usuário dele aqui).
   - **No dia** em que o número aparecer na nossa conta: me avisa → eu ligo o IVR nas linhas e publico. Você, na tela:
     nome "Poolheads Main Service", Call Recording ligado **sem** a mensagem (o IVR já fala); A2P do número; Felipe e
     Jorge entram no app LeadConnector com a conta nova; deskphone do Felipe apontado para a conta nova.
   - **Teste** (você): ligação em horário comercial atendida e não atendida, uma fora do horário, um SMS fora do horário.

## Testes que só você faz

6. **Ligações**: Nortex 469-238-2660 · Wrigley's LSA 925-744-7750 · Pool Duck LWR 941-541-5942 · IVR da Southern
   (214) 922-1914 (1 → Brett; 2 → 214-308-1744; sem resposta → caixa postal). Sem atender; me avisa.
7. **Google Lead Form "Weekly Pool Service Done Right"** — os workflows já estão no ar (lead → contato, tags, card,
   aviso à equipe, SMS de resposta). Falta ligar o form na tela, em **7 contas**: Wrigley's, BluVantage, Precision
   Pools, Pool Duck Wesley Chapel (na conta Pool Duck) — pedido da Val de 22/10 — e Reign, Damon's, Simple (de 19/10).
   1. Na sub-conta: Settings → Integrations → Google Ads → Manage → lead forms → "Weekly Pool Service Done Right" →
      **Map Fields** (nome, e-mail, telefone, CEP) → salvar → **Active** (botão Play).
   2. Teste: no Google Ads, campanha → Lead form → Edit → abrir o form → **Send Data**. O lead de teste dispara o aviso
      de lead novo para a equipe do cliente (se preferir, me avisa antes e eu desvio os avisos para você durante o teste).
   3. Me avisa: eu confiro contato, tags, card e aviso em cada uma e apago o teste.
8. **Forms de landing**: Southern (GOOGLE ADS - FORM em service.southernpoolandoutdoors.com) e Sunwave. Me avisa.

## UI do GHL / acessos

9. **Pool Keepers (Pool Profits), linha 805-262-9070** (encaminha para ela mesma, a ligação cai). Perguntado ao Frank se
   ainda precisa: a conta viva é a da BurchTech. Se precisar: Settings → Phone Numbers → Edit → *Forward calls to* =
   +1 805-457-8212; se não resolver, chamado no suporte do GHL:
   > Calls to our LC Phone number +1 (805) 262-9070 in the sub-account "The Pool Keepers" (location ID
   > hh6X9ht7Ay35b5I20aU2) don't connect: the call rings once or not at all and drops, and nothing shows up in the call
   > logs or conversations. Its forwarding number shows the number itself; it should forward to +1 805-457-8212. SMS from
   > this sub-account also failed on Oct 7 with "Trial mode not enabled for this agency". Could you check the number's
   > configuration and confirm the sub-account's phone system is fully active? Thank you.
10. **BurchTech**:
    - **Bluewater: terminado** (site → GHL no ar e testado; o que o Vik pediu — calculadora e PDFs avisando o Bill — e o
      resto dos forms). Falta só: mandar as 2 mensagens e **revogar a Application Password** (Users → Profile →
      Application Passwords → Revoke; não serviu, o host bloqueia).
    - **Pool Keepers**: snapshot carregado; nossos 28 workflows em **draft**, ajustados (Nathan, linha 805-457-8212,
      review, NPS, calendários). **Esperando o Frank/Nathan** decidirem o que liga (mensagem de 21/10); depois eu publico.
11. **Trocar os 3 refresh tokens** (Pool Profits, Pool Duck e BurchTech) colados no chat (`docs/get-firebase-token.md`).
12. **Master do snapshot**: corrigir (3 etapas Won e os bugs antigos) e dar Refresh em Agency → Account Snapshots.

## Esperando resposta (eu aplico quando chegar)

- **Pool Shack** (Rob): Skimmer já manda boas-vindas/pedido de review ao cliente semanal? Horário comercial é 9–17?
- **Stay Fresh IVR** (draft): Ed escolhe o nome da opção 2; Frank/Mike: sem tecla → Mike?, Kris sem atender → Mike?,
  quais linhas, fora do horário; depois as gravações em MP3.
- **Stay Fresh inativos** (arquivos no scratchpad, fora do git): tag do Ed (**não** "reactivation") + lista confirmada
  pelo Mike (Jen Knight está como cliente ativa). Depois eu importo.
- **Tags universais**: Frank/Ed aprovam os nomes → piloto na Pool Shack → snapshot + script.
- **LWR**: lembrete aos 32 promotores sai segunda 10:00 ET (eu confiro às 12:30 e mando os números).

## Outras decisões (perguntar ao Frank/Val quando der)

13. **Stay Fresh**: conferir os e-mails de teste com o texto do Mike; confirmação ao Frank, se ainda não mandou;
    campanha drain & wash: se quiser, passo os 2 workflows para draft.
14. **Nortex**: resposta ao Frank (texto de 20/10). Opcional (Fareed): endereço/cidade/CEP não obrigatórios no agendamento.
15. **Pool Duck LWR**: teste manual do form das landings, IDs de Ads/Pixel, Trustindex; alertas antigos "… - Steve" do WC.
16. Passion (linha Secondary, forms "PPC - … Quote") · Paid Ads na Bahama, Passion e Pool Shack (se não rodam, draft;
    na Pool Shack o "AdWords Form - New Lead" escuta um form que não existe mais) · Sunwave (conversão nas ligações da
    Adwords, número "Angi's Leads", redirecionamento quebrado, tag do Zap) · Wrigley's (follow-up nas ligações de
    AdWords/LSA) · BluVantage (bloquear `spam` no IVR) · tag por linha nas contas antigas · limpeza de drafts velhos.
