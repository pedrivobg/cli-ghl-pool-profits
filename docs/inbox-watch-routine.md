# Pedro Inbox Watch — n8n (03/11)

Roda no n8n (sem crédito do Claude): workflow **"Pedro Inbox Watch (ClickUp, Basecamp, Gmail)"**
(https://n8n.valenteai.cloud/workflow/ktHFt1DCNDSxWHjd), fuso America/Sao_Paulo.

- Quando roda: seg–sex, a cada 15 min das 9h às 12h45 (o shift) e de hora em hora das 13h às 19h.
- Fonte: Gmail de pedro@poolprofits.com, últimas 24 h. As notificações do ClickUp e do Basecamp chegam por e-mail,
  então cada e-mail é um item só e não há verificação dupla.
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
- Ações:
  - **Tarefa no ClickUp:** Team Space → To Do, atribuída ao Pedro, com prazo, estimativa e descrição. Não cria quando o
    item já é uma tarefa do ClickUp.
  - **Resposta automática**, só para a equipe interna:
    - comentário na tarefa do ClickUp (notificação de tarefa);
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
3. Conferir a credencial da OpenAI ("OpenAi Guiar", auto-atribuída) e a do ClickUp ("ClickUp account": tem que ser a
   sua).
4. Me avisar: eu rodo um teste e publico.

## Teste (03/11, dados simulados, nada enviado)

- 3 e-mails simulados:
  - menção no ClickUp → comentário na própria tarefa, sem tarefa nova, sem e-mail;
  - e-mail do Frank → tarefa + resposta por e-mail + e-mail ao Pedro;
  - Fyxer → descartado.
- Na tabela ficaram 2 linhas de teste (`TEST-1`, `TEST-2`). São inofensivas: os ids não existem no Gmail.
