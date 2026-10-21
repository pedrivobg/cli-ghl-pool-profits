# TODO do Pedro — só o que depende de você e ainda está aberto (21/10/2026)

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

9. **Pool Keepers — a linha que não funciona** (+1 805-262-9070; a ligação cai e não aparece nada no GHL). O número
   está configurado para encaminhar **para ele mesmo** desde 10/10 (a API não edita número).
   1. Settings → Phone Numbers → 805-262-9070 → Edit → *Forward calls to* = **+1 805-457-8212** → salvar e ligar.
   2. Se não salvar ou continuar caindo: **chamado no suporte do GHL** (texto pronto, é só colar):
      > Calls to our LC Phone number +1 (805) 262-9070 in the sub-account "The Pool Keepers" (location ID
      > hh6X9ht7Ay35b5I20aU2) don't connect: the call rings once or not at all and drops, and nothing shows up in
      > the call logs or conversations. The number was purchased on Oct 9 and its forwarding number shows the number
      > itself (+1 805-262-9070); it should forward to +1 805-457-8212. SMS from this sub-account also failed on
      > Oct 7 with "Trial mode not enabled for this agency". Could you check the number's configuration and confirm
      > the sub-account's phone system is fully active? Thank you.
   3. A2P dela também.
10. **BurchTech** (acesso por API desde 20/10):
    - **Bluewater**: GHL pronto e testado. O site nós mesmos ligamos (não o Vik): o código está pronto e testado aqui
      (`docs/bluewater-form-mapping.md`). Falta só **acesso ao WordPress** de bluewaterbrokerage.com: entrar em
      bluewaterbrokerage.com/wp-admin → Users → Profile → *Application Passwords* → nome "Claude" → *Add New
      Application Password* → me mandar o código + o seu usuário (precisa ser Administrator). Sem login: pedir ao Vik
      um usuário admin para pedro@poolprofits.com. ClickUp "GHL Form Mapping": corrigir o "waiting on Vik" (texto no
      chat de 20/10).
    - **Pool Keepers**: a conta viva é a da BurchTech (1.147 contatos). Snapshot só pela UI: Pool Profits → Account
      Snapshots → Create (sub-conta The Pool Keepers) → Share → copiar link; my.burchtech.app → Account Snapshots →
      Imported → colar → Sub-Accounts → The Pool Keepers → Load Snapshot, marcar **não sobrescrever** o que já existe.
      Me avisa: eu ajusto tudo pela API (Nathan nos avisos, números, custom values, NPS, link de review) e deixo em
      draft. Antes de publicar: decidir com o Frank/Nathan o que substitui os fluxos deles de form/chat e a "Customer
      Pipeline" (senão lead entra em dobro).
11. **Trocar os 3 refresh tokens** (Pool Profits, Pool Duck e BurchTech) colados no chat (`docs/get-firebase-token.md`);
    a Application Password da Bluewater, quando terminar, apaga no mesmo lugar onde criou.
12. **Master do snapshot**: corrigir (3 etapas Won e os bugs antigos) e dar Refresh em Agency → Account Snapshots.

## Respostas e decisões

- **Mandar hoje (textos no chat de 21/10)**: Pool Shack (Frank), IVR da Stay Fresh (Frank + Ed), lista de inativos
  da Stay Fresh (Frank + Ed), tags universais (Frank + Ed), resposta à Val sobre as reviews da LWR.
- **Pool Shack**: mudanças do Rob aplicadas e testadas (`docs/pool-shack-rob.md`). Esperando do Rob: o Skimmer já manda
  boas-vindas/pedido de review para o cliente semanal? (se sim, desligo só no semanal) · horário comercial é 9–17?
- **Stay Fresh IVR** (draft, nada ligado): Ed escolhe o nome da opção 2; Frank/Mike: quem atende sem tecla (hoje Mike),
  se o Kris não atender tenta o Mike antes da caixa postal?, as duas linhas ou só a do site/GBP, fora do horário.
  Depois: gravações em MP3 (eu troco a voz robótica pelos áudios) e publicar.
- **Stay Fresh inativos** (`<scratchpad>/stayfresh-inactive/`, fora do git): Ed escolhe a tag (**não usar
  "reactivation"**: dispara a campanha de reativação na hora); Mike confirma a lista (Jen Knight está como cliente
  ativa; Kate DiBenedetto estava com o e-mail da própria Stay Fresh). Depois eu importo.
- **Tags universais**: esperando o Frank/Ed aprovarem o formato (proposta no chat de 21/10); depois piloto na Pool Shack
  e o resto pelo snapshot + script.

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
