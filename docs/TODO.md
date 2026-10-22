# TODO do Pedro — só o que está aberto (22/10/2026)

O que já foi feito está em `docs/execucao-2026-10-13.md`. Testes são nossos: nada aqui vai para a equipe ou
para o cliente testar.

## Pool Profits (sub-contas da nossa agência)

1. **Encaminhamento** (Settings → Phone Numbers → número → Edit → *Forward calls to*): Cleverblu **689-229-3738 →
   +1 407-922-8947**. Poolheads 936-301-4150 só até a portabilidade (depois o IVR cobre; item 5).
2. **Ligação de teste** nas contas novas (Poolheads, Rosebrook, Cleverblu), sem atender: SMS de chamada perdida no seu
   celular + card em New Lead. Me avisa.
3. **A2P** dos números das contas novas (Settings → Phone System → Trust Center): sem aprovação o SMS não sai.
4. **Rosebrook**: comprar um número ("Website & GBP") + A2P; link de review do Google (Lynsey, ou conectar o Google
   Business Profile em Settings → Integrations). O Review Request fica em draft até ter o link.
5. **Poolheads — portabilidade do 936-314-9255** (conta GHL antiga → nossa). IVR e resposta fora do horário prontos em
   draft (`scripts/pp_poolheads_port.py`).
   - **Antes**: e-mail do **Jorge Arias** (crio o usuário dele aqui).
   - **No dia** em que o número aparecer na nossa conta: me avisa → eu ligo o IVR nas linhas e publico. Você, na tela:
     nome "Poolheads Main Service", Call Recording ligado **sem** a mensagem (o IVR já fala); A2P do número; Felipe e
     Jorge entram no app LeadConnector com a conta nova; deskphone do Felipe apontado para a conta nova.
   - **Teste** (você): ligação em horário comercial atendida e não atendida, uma fora do horário, um SMS fora do horário.
6. **Google Lead Form "Weekly Pool Service Done Right"**: os workflows já estão no ar (lead → contato, tags, card,
   aviso à equipe, SMS de resposta). Falta ligar o form na tela em **6 contas**: Wrigley's, BluVantage, Precision Pools
   (pedido da Val de 22/10), Reign, Damon's e Simple (de 19/10). A Pool Duck Wesley Chapel está em "Outras agências".
   1. Na sub-conta: Settings → Integrations → Google Ads → Manage → lead forms → "Weekly Pool Service Done Right" →
      **Map Fields** (nome, e-mail, telefone, CEP) → salvar → **Active** (botão Play).
   2. Teste: no Google Ads, campanha → Lead form → Edit → abrir o form → **Send Data**. O lead de teste dispara o aviso
      de lead novo para a equipe do cliente (se preferir, me avisa antes e eu desvio os avisos para você durante o teste).
   3. Me avisa: eu confiro contato, tags, card e aviso em cada uma e apago o teste.
7. **Forms de landing**: Southern (GOOGLE ADS - FORM em service.southernpoolandoutdoors.com) e Sunwave. Me avisa.
8. **Decidir (22/10)**:
   - **Review Request em todas as contas**: o "First Request?" está invertido desde o V9 (testado). Cliente sem nota
     sai do workflow, ou seja, nenhum cliente novo recebe pedido de nota ou de review. Correção: "NPS Score is empty".
     Libera?
   - **Limpar a master antes de importar na SwimReady**:
     - Sequential Call Routing = IVR da BluVantage (Fred/Paul, caixa postal "BluVantage", 6 números dela) → versão
       genérica;
     - número de Tucson no gatilho do AdWords Call In → tirar;
     - funis "Simple Pool Care" (3), "LP Teste" e o site duplicado → apagar;
     - logo "The Pool Care Pros" na página Schedule do funil "Pool Maintenance Snapshot" → logo da conta.
   - **SwimReady** (conta viva, sistema de março: 13 workflows, 6 publicados, funil de 10 etapas): a troca pelo
     snapshot novo é migração, como na Pool Keepers (nosso em draft + vigia, depois virada combinada). Quando?

### Esperando resposta (eu aplico quando chegar)

- **Pool Shack** (Rob): o Skimmer já manda boas-vindas/pedido de review ao cliente semanal? O horário comercial é 9–17?
- **Stay Fresh IVR** (draft): Ed escolhe o nome da opção 2; Frank/Mike: sem tecla → Mike?, Kris sem atender → Mike?,
  quais linhas, fora do horário; depois as gravações em MP3.
- **Stay Fresh inativos** (arquivos no scratchpad, fora do git): tag do Ed (**não** "reactivation") + lista confirmada
  pelo Mike (Jen Knight está como cliente ativa). Depois eu importo.
- **Tags universais**: Frank/Ed aprovam os nomes → piloto na Pool Shack → snapshot + script.

## Outras agências do GHL

### Pool Duck

- **Google Lead Form da Wesley Chapel**: mesmo passo a passo do item 6, na sub-conta Wesley Chapel da Pool Duck.
- **LWR**: o lembrete aos 32 promotores sai segunda (26/10) às 10:00 ET. Eu confiro às 12:30 e te mando os números.

### BurchTech

- **The Pool Keepers**: não depende de nós. Os nossos 28 workflows estão em draft e já ajustados (Nathan, linha
  805-457-8212, review, NPS, calendários). Estamos esperando o Frank/Nathan decidirem o que liga; depois eu publico.

## Geral

- **Trocar os 3 refresh tokens** (Pool Profits, Pool Duck e BurchTech) que foram colados no chat
  (`docs/get-firebase-token.md`).
