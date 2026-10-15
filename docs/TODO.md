# TODO — o que depende de você (atualizado 14/10/2026, fim do dia)

Só entra aqui o que não deu para resolver daqui depois de tentar. Conferido ao vivo em 14/10.

## Urgente

1. **Site da Passion manda os leads para outra conta do GHL** (conferido 14/10: continua igual).
   O código de passionpoolcare.com envia o form para um webhook da location
   `Y7wOLPd7DJ1UPHzcD8hG`, que não é da agência. Os leads do site não chegam na Passion.
   - Já existe na Passion o workflow **Website Webhook Lead To Pipeline**, testado com o mesmo
     payload do site. Falta quem mantém o site trocar `LEAD_WEBHOOK` pela URL de
     `docs/passion-webhook-url.txt`. Vale descobrir de quem é a `Y7wO…` (os leads antigos estão lá).
2. **Trocar os dois refresh tokens colados no chat**: Pool Profits e Pool Duck. Logout no GHL e
   gerar outro com `docs/get-firebase-token.md` (o da Pool Duck está num arquivo de env fora do repo).

## Testes que só você consegue fazer

3. **IVR da Southern** — nenhuma ligação desde que entrou no ar (conferido 14/10). Ligar para
   (214) 922-1914: apertar 1 → tem que tocar o celular do Brett (214) 893-2315; apertar 2 →
   (214) 308-1744; não atender → caixa postal e SMS "sorry we missed your call" no seu celular.
   Me avisar que eu confiro tags, gravação e card na conta.
4. **Review gate (NPS)**: na Test Snapshot, abrir o link do NPS de um contato de teste, responder 5 e
   ver o campo NPS Score ficar 5 (o captcha impede automatizar). Vale para as 6 contas.
5. **Kari (Southern)**: está em 🏆 Won - Weekly Pool Service. Se foi reparo/instalação, arrastar para
   o Won certo (com a tag `existing customer` nada dispara).

## Decisões (copy e negócio)

6. **Dois telefones nas mensagens**: umas usam `business_phone` (214-308-1744 na Southern), outras
   `a2p_verification_number` (214-922-1914, que agora é o número do IVR). Escolher um padrão.
7. **Paid Ads na Bahama, Passion e Pool Shack**: o AdWords Form está publicado e recebe o form da
   landing `go.*` (tag `adwords` + conversão no Google Ads). Se não rodam Ads para essa página, pôr
   os 08 Paid Ads em draft e rodar `pp_forms.py --only "<conta>" --apply`. Na Pool Shack ele escuta
   um form que não existe mais, então a conversão nunca dispara.
8. **A2P da Stay Fresh e da Pool Keepers**: workflows de SMS publicados, sem histórico de SMS para
   confirmar o A2P. Conferir em Settings → Phone System → Trust Center.
9. **Stay Fresh**:
   - draft antigo "Pool Smart OC Customers - SMS" (nome de outro cliente): revisar ou apagar;
   - 106 clientes ativos importados com a tag `active client` para a campanha de SMS do Frank;
     "Ryan Quitler" deve ser **Quilter** (e-mail quilterconstruction@) — aguardando o Frank.
10. **Sequential Call Routing** (do snapshot): toca usuários de outra conta e grava recado da
    BluVantage. Não dispara (números do gatilho não são das contas; na Southern está publicado, mas
    inofensivo). Apagar ou refazer no snapshot.

## Snapshot

11. **Corrigir o master e dar Refresh no snapshot V9.** A sub-conta **Snapshot Pool Profits** ainda
    tem os bugs corrigidos nas contas (merge fields quebrados, tarefas sem responsável/vencendo em
    1970, links de calendário, "Clear Pool Solutions Tucson" no AdWords Call In, notificação sem
    usuário) e só 1 etapa "Won" (as contas têm 3). Já está nela: texto do review sem "free month".
    Depois de corrigir (`pp_mirror` + `pp_fix`, quando você liberar), **Agency → Account Snapshots →
    Refresh** — a API não deixa fazer isso com o nosso token.

## Manual no GHL (sem API)

12. **Reputation → Settings → e-mail de review**: conferir o logo nas contas antigas (Southern,
    Bahama, Passion, Pool Shack, Pool Keepers).
13. **Sites com WPForms**: Pool Shack (thepoolshackarizona.com, forms 440/443), Bahama e Pool Keepers.
    Quando trocarem por form do GHL: form existente já cai no Website Form Fill; form novo → rodar
    `pp_forms.py --only "<conta>" --apply`.

## Pool Duck (outra agência) — detalhes em `docs/poolduck-lakewood-ranch.md`

14. **Campanha de review (Lakewood Ranch)**: pronta e testada, aguardando o cliente aprovar os textos.
    Aprovou → `pd_lwr_reviews.py launch` (274 clientes `turtle rock`, 37 excluídos). Confirmar com a
    Connie os 2 McQuaid (Ron não existe na conta).
15. **Landing pages LWR**:
    - teste manual do form em /google-landing-page e /fb-promo (captcha);
    - números de rastreamento Google e Facebook (cliente vai comprar) → eu ligo nas páginas e nos 2
      workflows "(Call In)", depois teste de ligação;
    - IDs de Google Ads/GTM/Meta Pixel do LWR, widget Trustindex do LWR, confirmar áreas e horários;
    - apagar os 2 contatos "TEST - Pool Duck setup" depois da revisão.
16. **Avisar**: os alertas de lead antigos do LWR ("… - Steve") não têm destinatário; no WC, o popup
    do form está configurado com o form "Poolfessionals AdWords" de outra empresa (ao vivo aparece o
    certo, mas vale reselecionar).

## BluVantage — detalhes em `docs/execucao-2026-10-13.md` (14/10)

17. **Mandar a resposta para Vanessa/Paul** (texto em inglês no chat de 14/10) e trazer as 3 decisões:
    - **bloquear spam**: um passo no começo do "Sequential Call Routing" (o IVR dos 6 números) que
      desliga quando o contato tem a tag `spam`. Mexe em toda ligação de entrada → só com o OK deles e
      uma ligação de teste junto;
    - **e-mail de lead** (o Paul perguntou): hoje nenhum form manda e-mail; dizer para quem mandar;
    - **"Out of Service Area"** também cancelar o texto NEW LEAD (precisa de tag nessa etapa)?
    (15/10: a pedido do Paul, ligação e SMS não mandam mais texto NEW LEAD; só os forms.)
18. ~~Chris Kelleher~~: a equipe ligou e marcou a avaliação para 21/10 às 11h (conferido 15/10).

## Orange Tree

19. **Orange Tree**: a Val reenvia o form do Facebook com dados novos e confirma o e-mail em
    orangetreepools@gmail.com (olhar Spam/Promoções). O celular do cliente (623) 974-5300 está com
    STOP desde 09/03: se quiserem voltar a receber os alertas por SMS, o cliente manda START para o
    número da conta. (E-mail de teste conferido por você; tag/card agora saem antes das notificações.)

## Pool Shack / demais contas

20. Tag `website & gbp` na linha Website & GBP está na Pool Shack (`pp_line_tag.py`). Se quiserem nas
    outras contas (e no master do snapshot), rodar com `--only "<conta>" --apply`.

## 15/10

21. **Pool Keepers — linha 805-262-9070 cai**: o encaminhamento está certo, mas a ligação nem chega ao
    GHL. Conferir no painel: Pool Keepers → Settings → Phone System (aviso de trial/suspensão/verificação)
    e Agency → Billing → carteira da Pool Keepers (Twilio rebilling ligado). Depois ligar de novo e me
    passar hora + número de origem.
22. **Orange Tree**: conferir na sua caixa o e-mail "🚨 New Facebook lead: TEST lead email" enviado pela
    conta da Orange Tree. Chegou → a conta envia; o cliente procura em Spam/Promoções ou filtro do Gmail.
    Não chegou → problema no envio de e-mail da sub-conta (Settings → Email Services).
23. **Sunwave**: a Val reenviar o form da landing (tags agora). Decidir se ligação da linha "Adwords"
    (407-864-6909) deve ganhar `adwords` + conversão: publicar o "AdWords Call In - New Lead" com esse número.

24. ~~BluVantage~~: e-mail de teste chegou completo (serviço e mensagem) — conferido por você 15/10. Falta só
    ver, na próxima submissão real, se ela aparece na conversa do contato.

## Concluído desde a versão anterior

- "Free month of service" removido do review positivo nas 16 contas do snapshot V9 (pedido do Ed).
- Won Stage nas 3 etapas Won, com ramificação (6 contas + Test Snapshot).
- IVR da Southern em todas as linhas, com o áudio; 1 → Brett, 2 → linha da empresa.
- Clique no card da oportunidade: Labs ativado por você.
- Duplicatas "DUPLICADO - não publicar" da Pool Shack e Pool Keepers: apagadas (conferido 14/10).
- Orange Tree: form/número do Google Ads virou Facebook (tags, alerta, origem); e-mail de lead para o
  cliente nos 3 caminhos (Facebook, site, chat).
- Stay Fresh: lista de clientes ativos importada.
- BluVantage: textos NEW LEAD sem spam/clientes; form do site ligado ao pipeline; aviso do form do
  Google Ads com destinatário; página de renovação conferida (no ar desde 12/10).

Obs.: a marcação "incompleto" que o GHL mostra nos passos "Add Task" é só visual — as tarefas são
criadas e atribuídas.
