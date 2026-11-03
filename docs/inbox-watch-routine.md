# Pedro Inbox Watch — n8n (03/11)

Roda no n8n (sem crédito do Claude): workflow **"Pedro Inbox Watch (ClickUp, Basecamp, Gmail)"**
(https://n8n.valenteai.cloud/workflow/ktHFt1DCNDSxWHjd), fuso America/Sao_Paulo.

- Quando roda: seg–sex, a cada 15 min das 9h às 12h45 (o shift) e de hora em hora das 13h às 19h.
- Fontes:
  - **ClickUp direto pela API** (últimas 26 h): todos os canais e DMs, respostas em thread (threads dos últimos 7
    dias onde eu participo, sou mencionado ou que estão em DM), tarefas novas atribuídas a mim ou que me citam na
    descrição, comentários em tarefas minhas / onde comentei / que me mencionam. Resposta vai no mesmo lugar (thread do
    chat ou comentário da tarefa).
  - **Gmail** pedro@poolprofits.com (últimas 24 h), incluindo as notificações do Basecamp. Os e-mails do ClickUp são
    descartados (o ClickUp já é lido direto), para não haver item duplicado.
- Ruído descartado: Fyxer, newsletters, recibos, Zoom, LinkedIn, calendário.
- Atraso natural: o item só é tratado depois de 5 min, então a resposta sai entre 5 e 20 min.
- Registro: tabela do n8n "Pedro Inbox Ledger" (`wb0SlsU03MQ4xdgv`). Item já registrado não é tratado de novo.
- A IA (OpenAI, temperatura 0.1) classifica cada item:
  - se pede algo ao Pedro;
  - cliente;
  - se o cliente vê a conversa;
  - resumo em PT;
  - nome e descrição da tarefa, estimativa, prazo e prioridade;
  - resposta curta em inglês, que nunca diz "pronto";
  - se precisa do Pedro e se é urgente.
- Proatividade: 9h30, se nada chegou desde a véspera, mensagem no canal "Pool Profits" do ClickUp marcando Frank e Val
  ("anything you need on GHL today?", 3 variações). 12h50: atualização de fim de shift no mesmo canal com as minhas
  tarefas abertas e o prazo de cada uma.
- Tarefas vão para a lista "Pedro – GHL & Automations" (`901422915733`). Respostas sempre em primeira pessoa (eu = Pedro).
- Ações:
  - **Tarefa no ClickUp:** lista "Pedro – GHL & Automations", atribuída ao Pedro, com prazo, estimativa e descrição. Não cria quando o
    item já é uma tarefa do ClickUp.
  - **Resposta automática**, só para a equipe interna:
    - resposta na mesma thread do chat do ClickUp ou comentário na tarefa;
    - resposta por e-mail quando o remetente é @poolprofits.com e da equipe.
  - Basecamp e qualquer conversa que o cliente vê: **nunca** responde.
  - **E-mail ao Pedro** ("[Pool Profits] Ação/URGENTE: …") quando precisa dele: aprovação, teste humano, decisão,
    conversa com cliente (vai com o rascunho da resposta) ou urgência.

O trabalho em si (GHL, scripts) continua sendo feito numa sessão com o Claude, a partir da tarefa ou do e-mail.

## Para ligar (Pedro, no n8n)

1. Credentials → New → Gmail OAuth2 → entrar com **pedro@poolprofits.com**. Hoje os 3 nós de Gmail estão com
   "Gmail Valente" (auto-atribuída), que é outra conta e não lê nem responde como você.
2. No workflow, trocar a credencial nos nós "Get recent emails to Pedro", "Acknowledge by email (team only)" e
   "Email Pedro (needs you)".
3. **ClickUp**: a credencial "ClickUp account" do n8n é de outro workspace (a API responde "Workspace not
   authorized"). Criar uma nova: ClickUp (Pool Profits) → avatar → Settings → Apps → API Token → Generate/Copy; no n8n
   Credentials → New → ClickUp API → colar o token → nome "ClickUp Pool Profits". Trocar em todos os nós de ClickUp.
4. Conferir a credencial da OpenAI ("OpenAi Guiar", auto-atribuída).
5. Me avisar: eu rodo um teste e publico.

## Teste (03/11, dados simulados, nada enviado)

- 3 e-mails simulados:
  - menção no ClickUp → comentário na própria tarefa, sem tarefa nova, sem e-mail;
  - e-mail do Frank → tarefa + resposta por e-mail + e-mail ao Pedro;
  - Fyxer → descartado.
- Na tabela ficaram 2 linhas de teste (`TEST-1`, `TEST-2`). São inofensivas: os ids não existem no Gmail.
