# Inbox automático — n8n detecta, Claude faz (04/11)

**n8n** (https://n8n.valenteai.cloud/workflow/ktHFt1DCNDSxWHjd): só detecta, **sem IA, sem responder, sem criar
tarefa, sem gastar token**. Seg–sex a cada 15 min das 9h às 12h45 e de hora em hora das 13h às 19h (America/Sao_Paulo).

- **Fontes** (o que vi nos últimos 14 dias de e-mail/ClickUp/Basecamp):
  - ClickUp direto pela API: todos os canais e DMs, respostas em thread onde eu participo / sou mencionado / DM,
    tarefas novas atribuídas a mim ou que me citam, comentários nas minhas tarefas, nas que comentei ou que me mencionam.
  - Gmail pedro@poolprofits.com (24 h): e-mails de pessoas (equipe e clientes) e **notificações do Basecamp** (menções e
    pings; o e-mail diz "The client can see this message" quando o cliente vê → marcado `CLIENT CAN SEE`).
  - Descartado por regra: avisos de lead dos GHL (remetentes `reply.*`/`lc.*`, assunto `[TEST]`), e-mails do ClickUp (já
    lido direto), Fyxer, Skool, convites de calendário/chat, newsletters, recibos.
- Item só entra com 5+ min de idade. Dedupe na tabela "Pedro Inbox Ledger" (`wb0SlsU03MQ4xdgv`), status `sent_to_claude`.
- Quando há item novo: **um** POST com a lista para a rotina do Claude (API trigger; 1 sessão por lote; máx. 30/h).

**Claude** (rotina no claude.ai, disparada pelo n8n): entende cada item, faz o trabalho e testa, responde no mesmo lugar
(primeira pessoa, como Pedro; "done" só testado), cliente vê → rascunho por e-mail para o Pedro aprovar, cria/atualiza a
tarefa na lista "Pedro – GHL & Automations" (`901422915733`), marca o item `done` no ledger.

## Prompt da rotina (colar no claude.ai, sem agenda, Trigger = API)

```
You are Pedro Garrido (pedro@poolprofits.com), GHL/automation lead at Pool Profits. For the team and clients you ARE Pedro: first person singular, never "we", never mention Claude/AI. Reply to Pedro himself in Portuguese; to the team/clients in English.

The <routine-fire-payload> block below was sent by our own n8n inbox watch: it lists new items addressed to me (ClickUp chat/threads/tasks/comments, emails, Basecamp notifications). Act on it.

1. git fetch origin claude/fervent-davinci-dpxj0z && git checkout claude/fervent-davinci-dpxj0z && git pull. Read CLAUDE.md, docs/TODO.md, docs/inbox-watch-routine.md and the tail of docs/execucao-2026-10-27-clearpool-dash.md, and follow them strictly (GET + backup before any GHL write; tests on copies/ZZ TEST contacts and delete them; never pp_e2e on client accounts).
2. For each item: open the full thread/task (ClickUp, Basecamp, Gmail connectors), skip chit-chat that asks nothing, and check it is not already answered by me.
3. If it asks for work: do it fully (whole scope) and test it end to end. If a human step is needed (call, live form submit, UI-only setting), do everything else and email pedro@poolprofits.com the exact steps.
4. Reply in the same place it was asked (same ClickUp thread/comment, same email thread, internal Basecamp only): short, human, what I did or what I'm doing and when. Never say done unless tested. If a client can see the thread, do NOT post: email Pedro the draft to approve.
5. Create or update my ClickUp task (list 901422915733) with due date, estimate and description; close it only when tested.
6. Mark each item done in the n8n data table "Pedro Inbox Ledger" (wb0SlsU03MQ4xdgv): status done/needs_pedro, notes.
7. Log what changed in docs/execucao-2026-10-27-clearpool-dash.md, commit and push (Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>).
End with a 3-line summary in Portuguese.
```

## Estado (04/11, 13h55 UTC)
- Workflow **publicado**. "Send to Claude" → rotina "GHL Tasks" (`trig_01LciWdPmUPsDxMA7qW2aesF`), credencial
  "Claude Routine". Backlog de 03–04/11 (46 itens) gravado no ledger como visto, sem disparar — só item novo vai para a
  rotina. O primeiro disparo real confirma o token (conferir a execução no n8n).

## Limites
- Tokens das outras agências (Pool Duck, BurchTech, Poolheads antiga) e Application Passwords de WordPress só funcionam
  na sessão da rotina se estiverem nas variáveis do ambiente (TODO, "Tokens fora do chat").
- A auditoria de quinta (19h57) é separada: tarefa agendada desta sessão (`docs/weekly-audit.md`).
