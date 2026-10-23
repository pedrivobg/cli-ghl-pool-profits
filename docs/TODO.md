# TODO do Pedro — só o que está aberto (23/10/2026)

O que já foi feito está em `docs/execucao-2026-10-13.md`. Testes são nossos: nada aqui vai para a equipe ou
para o cliente testar.

## Pool Profits (sub-contas da nossa agência)

Instruções do dia 24/10 para quem ajuda o Pedro (com as fichas de A2P; tem EIN, fica fora do git):
`reports/Instrucoes 24-10 - TODO Pool Profits.pdf`. Encaminhamento da Cleverblu feito em 23/10 (conferido).

1. **Ligação de teste** nas contas novas (Rosebrook, Cleverblu), sem atender: SMS de chamada perdida no seu
   celular + card em New Lead. **Só depois do A2P aprovado** (a da Cleverblu toca o celular do dono).
2. **A2P** (Settings → Phone System → Trust Center): sem aprovação o SMS não sai.
   - Cleverblu: ninguém enviou; registrar em 24/10 com a ficha (site e política/termos do próprio site deles,
     cleverblu.com/policy/…; os custom values `privacy_policy`/`terms_of_use` vazios foram preenchidos com essas
     páginas em 23/10, o que conserta os links do form de consentimento).
   - Poolheads: print do Trust Center (Brand/Campaign). Brand aprovada → registrar só a campanha; Brand pedindo
     registro → não enviar (o Frank disse que enviou).
   - Rosebrook e Blissful: faltam número e dados. EIN da Rosebrook no onboarding com 8 dígitos; Blissful sem
     endereço; nenhum dos dois sites tem política de privacidade → site "New A2P Verification" num subdomínio deles
     (precisa do DNS do cliente). Pedir ao Frank.
3. **Rosebrook**: comprar um número ("Website & GBP") + A2P; link de review do Google (Lynsey, ou conectar o Google
   Business Profile em Settings → Integrations). O Review Request fica em draft até ter o link.
4. **Poolheads: número já na nossa conta (22/10)**. O IVR "Business Hours Call Routing" (pasta 09 System) e o "After
   Hours Message" estão no ar nas 3 linhas (936-314-9255, 936-243-1724 e 936-301-4150). O IVR toca o app do Felipe e
   o celular dele, e a caixa postal usa a gravação deles. Os outros 29 workflows estão em draft (alguém pausou hoje,
   como o Frank pediu).
   - **Teste**: feito pelas ligações do Frank em 22/10 (15:15 CT → IVR, caixa postal com a gravação deles; 17:17 CT →
     mensagem de fora do horário). Os SMS dessas ligações saíram "failed": falta o A2P (item 2).
   - **Na tela**: Settings → Phone Numbers → 936-314-9255 → Call Recording ligado **sem** a mensagem (o IVR já fala).
     Felipe (e Jorge) no app LeadConnector com a conta nova; deskphone do Felipe apontado para a conta nova.
   - **E-mail do Jorge Arias**: crio o usuário dele e coloco no IVR.
   - **Depois do A2P** (o Frank enviou): republicar o "Missed New Lead", que manda o texto de chamada perdida deles,
     e o resto das nossas automações quando o Frank liberar.
   - **Conta antiga → nossa (Frank, 22/10: "copy over everything" + contatos)**. Para isso preciso do token da conta
     antiga:
     1. avisar o Frank na hora (o login manda código de verificação para info@poolheadscare.com, o e-mail do
        cliente);
     2. Chrome → app.gohighlevel.com com o login que o Frank mandou + o código;
     3. abrir a sub-conta da Poolheads → Ctrl+Shift+J → colar o trecho de `docs/get-firebase-token.md` → Enter;
     4. colar o token no chat.

     Com ele eu:
     - copio **todos** os workflows (inclui os de anúncio: Google Service Ads, Google Repair Ads, LVB Meta) em draft,
       numa pasta "Conta antiga", com "[Old]" nos nomes repetidos;
     - trago **todos os contatos** (tags, campos, DND; sem duplicar; tag "imported from old account");
     - trago as oportunidades, se quiserem.
5. **Google Lead Form "Weekly Pool Service Done Right"**: workflows no ar; form mapeado e ativo (23/10) em Wrigley's,
   BluVantage e Precision, e já estava em Reign e Damon's (caminho atual: Settings → Integrations → card "Google Lead
   Ads" → Manage → aba "Manage Google Ads" → ▶ Setup Form Mapping). Nenhum lead por lead form até 23/10 em nenhuma.
   - **Simple**: "Lead ad forms not available": a conta de Google Ads ligada no GHL (258-800-5448) não tem o form →
     perguntar à Val em que conta ele está.
   - **Teste** (24/10): avisar antes → eu desvio os avisos → Send Data em cada conta (Google Ads → campanha → Lead form →
     Edit → abrir o form → Send Data) → eu confiro contato, tags, card e aviso, apago o teste e volto os avisos.
6. **Blissful Waters (conta nova, 22/10)**: pronta no padrão (fuso, usuário Brian em avisos/tarefas/dono, link de
   review, NPS; 0 erro). Falta:
   - comprar um número ("Website & GBP") + A2P (sem número, nenhum SMS sai: nem para o cliente nem o aviso para o
     Brian). Por enquanto o `a2p_verification_number` está com o telefone da empresa (210) 360-1611;
   - o Brian e o Jason fazerem o primeiro acesso ("Forgot password" em app.poolprofits.com) e instalarem o app;
   - conectar o Google Business Profile (as respostas automáticas a reviews dependem disso);
7. **BluVantage: 3 forms das landing pages novas** (pedido da Val, 22/10). Prontos, com workflows no ar e testados
   pela API. Teste final: quando o Atif puser os forms nas páginas, mandar um envio de cada. Me avisa antes e eu
   desvio os avisos da equipe para você.
8. **Form de landing da Southern** (GOOGLE ADS - FORM em service.southernpoolandoutdoors.com): nenhum envio desde
   16/10. Teste junto com o do item 5 (avisos ao Brett desviados): enviar e conferir que vai para a página de obrigado
   (`/ty-page-2934-3692`). A Sunwave está confirmada pelo lead real de 17/10 (tags, card, follow-ups).
9. **SwimReady** (conta viva, sistema de março: 13 workflows, 6 publicados, funil de 10 etapas): a troca pelo snapshot
    novo é uma migração, como na Pool Keepers (o nosso entra em draft com o vigia, depois a virada combinada).
    Perguntado ao Ed junto com o PDF: quando o Jeremy quer virar. Jeremy (23/10) aprovou a abordagem e vai mandar
    ajustes de texto e tom por código: os M/A do PDF são os do master de 22/10 (`reports/snapshot-guide/
    swimready-pool-service.html` guarda essa numeração; o master mudando, os códigos de um PDF novo mudam). Os ajustes
    entram como `config/swimready_wording.json` + `pp_wording.py` na migração.

### Esperando resposta (eu aplico quando chegar)

- **Pool Shack** (Rob): o Skimmer já manda boas-vindas/pedido de review ao cliente semanal? O horário comercial é 9–17?
- **Stay Fresh IVR** (draft): Ed escolhe o nome da opção 2; Frank/Mike: sem tecla → Mike?, Kris sem atender → Mike?,
  quais linhas, fora do horário; depois as gravações em MP3.
- **Stay Fresh inativos** (arquivos no scratchpad, fora do git; Frank pediu a confirmação ao Mike no Basecamp em 23/10
  e repassa): tag do Ed (**não** "reactivation") + lista confirmada
  pelo Mike (Jen Knight está como cliente ativa). Depois eu importo.
- **Tags universais**: Frank/Ed aprovam os nomes → piloto na Pool Shack → snapshot + script.
- **Ekahi** (PDF de revisão das automações, 22/10, Frank → Erik no Basecamp): Erik aprova/pede mudanças por código e
  responde D1–D8 (cliente que liga tratado como lead novo, dois textos na chamada perdida e no form, link de agenda
  vazio, cliente ativo caindo no follow-up de lead e em Lost, texto de primeira visita 1 h depois do Won, lembrete
  único, win-back que continua depois da resposta). Config: `config/review/ekahi-solutions-llc.json`.

## Outras agências do GHL

### Pool Duck

- **Google Lead Form da Wesley Chapel**: mesmo passo a passo do item 6, na sub-conta Wesley Chapel da Pool Duck.
- **LWR**: o lembrete aos 32 promotores sai segunda (26/10) às 10:00 ET. Eu confiro às 12:30 e te mando os números.
- **Franchising — feira de Tampa** (Lee): a sequência está no ar para 72 leads e vai até quinta, 29/10; não depende de
  você. Se o Lee quiser outro link em algum SMS, eu troco (vale para quem ainda está na espera).

### BurchTech

- **The Pool Keepers**: não depende de nós. Os nossos 28 workflows estão em draft e já ajustados (Nathan, linha
  805-457-8212, review, NPS, calendários). Estamos esperando o Frank/Nathan decidirem o que liga; depois eu publico.

## Geral

- **Trocar os 3 refresh tokens** (Pool Profits, Pool Duck e BurchTech) que foram colados no chat
  (`docs/get-firebase-token.md`).
