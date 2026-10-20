# TODO do Pedro — só o que depende de você e ainda está aberto (20/10/2026)

O que já foi feito está em `docs/execucao-2026-10-13.md`. Testes são nossos: nada aqui vai para a equipe ou
para o cliente testar.

## Contas novas (Poolheads, Rosebrook, Cleverblu) — automações prontas, faltam só coisas de UI

1. **Encaminhamento das linhas** (sem API; hoje a ligação só toca no app web do GHL): Settings → Phone Numbers →
   número → Edit → *Forward calls to*:
   - Poolheads **936-301-4150 → +1 936-314-9255**
   - Cleverblu **689-229-3738 → +1 407-922-8947**
2. **Ligação de teste** em cada uma, depois do item 1, sem atender. Tem que chegar o SMS de chamada perdida no
   seu celular e aparecer o card em New Lead com a tarefa. Me avisa que eu confiro tags, card e aviso.
3. **A2P** dos dois números (Settings → Phone System → Trust Center): sem aprovação o SMS não sai.
4. **Rosebrook**:
   - **Número**: comprar um (nome "Website & GBP") e fazer o A2P. Sem número, nenhum SMS sai, nem o aviso de
     lead para a Lynsey. Depois eu ponho o número no custom value, crio a tag da linha e confiro.
   - **Link de review do Google**: pedir à Lynsey ou conectar o Google Business Profile em Settings →
     Integrations. O Review Request fica em draft até ter o link.

## Testes que só você faz

5. **Nortex**: ligação no 469-238-2660 sem atender (SMS de chamada perdida + card).
6. **Ligações**: Wrigley's LSA 925-744-7750 · Pool Duck LWR 941-541-5942 · IVR da Southern (214) 922-1914
   (1 → Brett; 2 → 214-308-1744; sem resposta → caixa postal).
7. **Google Lead Form** (Reign, Damon's, Simple; form "Weekly Pool Service Done Right"):
   1. Na sub-conta, Settings → Integrations → Google Ads → Manage: o form tem que estar mapeado (nome,
      telefone, e-mail, CEP) e **Active**.
   2. No Google Ads: campanha → Lead form → Edit → abrir o form → **Send Data**.
   3. Me avisa e eu confiro e apago o teste.
8. **Forms de landing** (envio não automatizável):
   - Southern: GOOGLE ADS - FORM em service.southernpoolandoutdoors.com.
   - Sunwave: form da landing.
   - Me avisa depois de enviar.

## UI do GHL / acessos

9. **Pool Keepers**: 805-262-9070 encaminha para ela mesma. Trocar para **+1 805-457-8212** (mesmo caminho do
   item 1) e ligar para testar. A2P dela também.
10. **BurchTech (Bluewater + Pool Keepers)** — o ClickUp "GHL Form Mapping" é isto, plano pronto em
    `docs/bluewater-form-mapping.md`: aguardando o login/acesso que você pediu ao Ed (o projeto não estava no
    Basecamp). Com acesso:
    - **Para mim**: refresh token por API (`docs/get-firebase-token.md`) ou pedro@poolprofits.com como admin.
    - **Snapshot**: da sub-conta The Pool Keepers → Share → importar na BurchTech. É só na UI; o resto eu refaço.
11. **Trocar os 2 refresh tokens** (Pool Profits e Pool Duck) colados no chat (`docs/get-firebase-token.md`).
12. **Master do snapshot**: corrigir (3 etapas Won e os bugs antigos) e dar Refresh em Agency → Account Snapshots.

## Respostas e decisões

13. **Stay Fresh**:
    - Conferir os 7 e-mails de teste com o texto do Mike em pedro@poolprofits.com.
    - Mandar ao Frank a confirmação (texto no chat de 20/10), se ainda não mandou.
    - Campanha drain & wash: se quiser, eu passo os 2 workflows para draft.
14. **Nortex** (no lugar do Zoom): form do site → agenda preenchida no ar, testado por você; telefone com seletor
    de país. Falta só mandar a resposta ao Frank (texto no chat de 20/10). Opcional, decisão do Fareed: tirar a
    obrigatoriedade de endereço/cidade/CEP no form de agendamento.
15. **Pool Duck LWR**: teste manual do form das landings, IDs de Ads/Pixel, Trustindex; avisar o WC dos alertas
    antigos "… - Steve" sem destinatário.
16. **Decisões em aberto** (perguntar ao Frank/Val quando der):
    - Passion: a linha Secondary (629-324-1486) serve para quê? Os forms "PPC - … Quote" recebem anúncio?
    - Paid Ads na Bahama, Passion e Pool Shack: rodam Ads para a landing `go.*`? Se não, draft.
    - Sunwave: conversão do Google Ads nas ligações da Adwords? Trocar o número "Angi's Leads" (só recebe spam)?
      Avisar a Val do redirecionamento quebrado de sunwavepoolpros.com e da tag do Zap.
    - Wrigley's: SMS de follow-up também nas ligações do AdWords/LSA?
    - BluVantage: bloquear no IVR quem tem tag `spam`?
    - Tag por linha e SMS com a linha rastreada nas contas antigas que ainda não têm.
    - Limpeza: drafts velhos da Stay Fresh e o "Sequential Call Routing" (IVR da BluVantage) nas contas antigas.
