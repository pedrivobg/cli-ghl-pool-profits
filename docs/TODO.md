# TODO do Pedro — só o que está aberto (22/10/2026)

O que já foi feito está em `docs/execucao-2026-10-13.md`. Testes são nossos: nada aqui vai para a equipe ou
para o cliente testar.

## Pool Profits (sub-contas da nossa agência)

1. **Encaminhamento** (Settings → Phone Numbers → número → Edit → *Forward calls to*): Cleverblu **689-229-3738 →
   +1 407-922-8947**.
2. **Ligação de teste** nas contas novas (Rosebrook, Cleverblu), sem atender: SMS de chamada perdida no seu
   celular + card em New Lead. Me avisa.
3. **A2P** dos números das contas novas (Settings → Phone System → Trust Center): sem aprovação o SMS não sai.
4. **Rosebrook**: comprar um número ("Website & GBP") + A2P; link de review do Google (Lynsey, ou conectar o Google
   Business Profile em Settings → Integrations). O Review Request fica em draft até ter o link.
5. **Poolheads: número já na nossa conta (22/10)**. O IVR "Business Hours Call Routing" (pasta 09 System) e o "After
   Hours Message" estão no ar nas 3 linhas (936-314-9255, 936-243-1724 e 936-301-4150). O IVR toca o app do Felipe e
   o celular dele, e a caixa postal usa a gravação deles. Os outros 29 workflows estão em draft (alguém pausou hoje,
   como o Frank pediu).
   - **Teste** (você): agora, fora do horário, cai na caixa postal com a gravação deles. Amanhã, entre 9 e 17, testar
     uma ligação atendida e uma não atendida, mais um SMS fora do horário.
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
6. **Google Lead Form "Weekly Pool Service Done Right"**: os workflows já estão no ar (lead → contato, tags, card,
   aviso à equipe, SMS de resposta). Falta ligar o form na tela em **6 contas**: Wrigley's, BluVantage, Precision Pools
   (pedido da Val de 22/10), Reign, Damon's e Simple (de 19/10). A Pool Duck Wesley Chapel está em "Outras agências".
   1. Na sub-conta: Settings → Integrations → Google Ads → Manage → lead forms → "Weekly Pool Service Done Right" →
      **Map Fields** (nome, e-mail, telefone, CEP) → salvar → **Active** (botão Play).
   2. Teste: no Google Ads, campanha → Lead form → Edit → abrir o form → **Send Data**. O lead de teste dispara o aviso
      de lead novo para a equipe do cliente (se preferir, me avisa antes e eu desvio os avisos para você durante o teste).
   3. Me avisa: eu confiro contato, tags, card e aviso em cada uma e apago o teste.
7. **Blissful Waters (conta nova, 22/10)**: pronta no padrão (fuso, usuário Brian em avisos/tarefas/dono, link de
   review, NPS; 0 erro). Falta:
   - comprar um número ("Website & GBP") + A2P (sem número, nenhum SMS sai: nem para o cliente nem o aviso para o
     Brian). Por enquanto o `a2p_verification_number` está com o telefone da empresa (210) 360-1611;
   - o Brian e o Jason fazerem o primeiro acesso ("Forgot password" em app.poolprofits.com) e instalarem o app;
   - conectar o Google Business Profile (as respostas automáticas a reviews dependem disso);
8. **BluVantage: 3 forms das landing pages novas** (pedido da Val, 22/10). Prontos, com workflows no ar e testados
   pela API. Teste final: quando o Atif puser os forms nas páginas, mandar um envio de cada. Me avisa antes e eu
   desvio os avisos da equipe para você.
9. **Forms de landing**: Southern (GOOGLE ADS - FORM em service.southernpoolandoutdoors.com) e Sunwave. Me avisa.
10. **SwimReady** (conta viva, sistema de março: 13 workflows, 6 publicados, funil de 10 etapas): a troca pelo snapshot
    novo é uma migração, como na Pool Keepers (o nosso entra em draft com o vigia, depois a virada combinada).
    Perguntado ao Ed junto com o PDF: quando o Jeremy quer virar.

### Esperando resposta (eu aplico quando chegar)

- **Pool Shack** (Rob): o Skimmer já manda boas-vindas/pedido de review ao cliente semanal? O horário comercial é 9–17?
- **Stay Fresh IVR** (draft): Ed escolhe o nome da opção 2; Frank/Mike: sem tecla → Mike?, Kris sem atender → Mike?,
  quais linhas, fora do horário; depois as gravações em MP3.
- **Stay Fresh inativos** (arquivos no scratchpad, fora do git): tag do Ed (**não** "reactivation") + lista confirmada
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
