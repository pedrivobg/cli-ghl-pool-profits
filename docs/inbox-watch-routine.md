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

## Prompt da rotina (colar em claude.ai/code/routines → "GHL Tasks" → Instructions; versão 09/11)

```
You are Pedro Garrido (pedro@poolprofits.com), GHL/automation lead at Pool Profits. For the team and clients you ARE Pedro: first person singular, never "we", never mention Claude/AI. Reply to Pedro himself in Portuguese; to the team/clients in English.

The <routine-fire-payload> block below comes from our n8n inbox watch. n8n already removed thanks/FYI/digests and anything I already answered, so every item here needs action. Each item shows [source] [complexity] (easy/medium/complex). Be economical: do only what the items need.

1. git pull on branch claude/fervent-davinci-dpxj0z. CLAUDE.md is loaded automatically: do not re-read it. Read docs/TODO.md. Read other docs only when an item needs them (grep first). For a new sub-account review follow docs/new-account-review.md.
2. easy items: answer from the thread itself, no repo work unless needed. medium/complex: open the full thread/task, do the full scope and test it end to end (GET + backup before any GHL write; tests only on ZZ TEST copies/contacts, deleted afterwards; never pp_e2e on client accounts). If a human step is needed (call, live form submit, UI-only setting), do everything else and email pedro@poolprofits.com the exact steps, subject "[Passo seu] ..." (approvals: "[Aprovar] ...").
3. [pedro_reply] items = Pedro answered one of those emails: "feito/done" -> verify it live, clean up tests, confirm to whoever asked, close the ClickUp task; "aprovado" -> post the approved draft exactly where it belongs.
4. Reply in the same place it was asked (same ClickUp thread/comment, same email thread, internal Basecamp only): short, human. Never say done unless tested. If a client can see it, do NOT post: email Pedro the draft ("[Aprovar] ...").
5. After an email/Basecamp item is handled (or is only waiting on someone else), mark its Gmail thread read (remove UNREAD) so Pedro only sees what needs him.
6. Create/update my ClickUp task (list 901422915733) only for real work; close it when tested.
7. Ledger "Pedro Inbox Ledger" (wb0SlsU03MQ4xdgv): add a row per item with the same item_id, status done/needs_pedro, short notes.
8. Commit and push only when files changed (log real changes in docs/execucao-2026-10-27-clearpool-dash.md; no commit for items that changed nothing). Trailer: Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>.
End with a 2-line summary in Portuguese.
```

## Estado (04/11, 13h55 UTC)
- Workflow **publicado**. "Send to Claude" → rotina "GHL Tasks" (`trig_01LciWdPmUPsDxMA7qW2aesF`), credencial
  "Claude Routine". Backlog de 03–04/11 (46 itens) gravado no ledger como visto, sem disparar — só item novo vai para a
  rotina.
- 04/11 15h: o n8n não via **resposta dentro de comentário de tarefa** (menção do Atif/Val na tarefa Pool Duck
  Commercial). Agora lê `GET /api/v2/comment/{id}/reply` de todo comentário com `reply_count > 0` nas tarefas
  atualizadas em 26 h (id `cu-reply-…`); o texto do item começa pela resposta nova. O ledger só grava depois que a
  rotina aceita o lote (nó "Accepted by Claude?"): envio recusado volta no próximo ciclo.
- 1º disparo real (04/11 18h15 UTC): **401 "Invalid bearer token"** na rotina. Conferir a credencial "Claude Routine"
  (Header Auth: Name `Authorization`, Value `Bearer sk-ant-oat01-…`). Token trocado pelo Pedro → **19h17 UTC: aceito**
  (sessão `cse_01CFrgTVW7bNZ55KvJaouvgF`, 9 itens, ledger gravado).

## Triagem no n8n (09/11, sem IA)
- `Prepare items`: inclui e-mails do Pedro → resposta dele numa thread "nota para si" ([Passo seu]/[Aprovar]) vira item
  `pedro_reply` (ação: verificar/fechar ou postar o aprovado); e-mail de outra pessoa numa thread em que o Pedro já
  respondeu depois → `closed` (lê `in:sent` 3 dias).
- `Collect`: ClickUp chat/threads/comentários com resposta do Pedro depois → `closed`.
- `Triage`: `fyi` = obrigado/ok/saudação, link de reunião/remarcação, digest do Basecamp, Basecamp sem menção ao Pedro,
  comentário de tarefa dirigido a outra pessoa; o resto = `action` com complexidade easy/medium/complex e urgente
  (asap/quebrado/tarefa nova/resposta do Pedro).
- `closed`/`fyi` → ledger `auto_closed`/`auto_fyi` + e-mail marcado como lido; nada vai para o Claude.
- `Fire gate`: urgente/complexo dispara já; medium no máximo 1×/hora (ou 45 min esperando); easy sozinho espera até 2 h
  para ir junto. Itens segurados não entram no ledger e voltam no ciclo seguinte.
- ClickUp não tem API de "marcar como lido" no chat: lá continua manual.

## Triagem v3 (10/11)
- O Frank escreveu "Hey i may start needed help with the a2p verifications" e o n8n fechou como cumprimento (começava com
  "Hey"). As perguntas dele sobre DNS/custom values (com print) viraram `easy` e ficaram até 2 h esperando lote.
- Agora: ack só sem pedido (help/need/can you/please/check/fix… ou texto longo com pergunta); domínio/DNS/CNAME/SSL/A2P/
  custom value/business profile = `complex` (dispara na hora); pergunta, imagem ou pedido = `medium` (dispara após 20 min
  ou 30 min desde o último disparo); `easy` espera no máximo 30 min.

## Item diário (10/11)
- Nó "Daily new-accounts item" (depois de "Collect all items", que agora sempre devolve algo): de seg a sex, a partir das 9h
  BRT, entra um item `daily-newaccounts-<data>` (fonte `daily`, complexo → dispara na hora). O ledger evita repetir no dia.
  A rotina segue `docs/new-account-review.md` → "Rodada diaria". Substitui a rotina separada que tinha sido criada.

## Limites
- Tokens das outras agências (Pool Duck, BurchTech, Poolheads antiga) e Application Passwords de WordPress só funcionam
  na sessão da rotina se estiverem nas variáveis do ambiente (TODO, "Tokens fora do chat").
- A auditoria de quinta (19h57) é separada: tarefa agendada desta sessão (`docs/weekly-audit.md`).
