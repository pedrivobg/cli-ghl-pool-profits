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

## Prompt da rotina (colar em claude.ai/code/routines → "GHL Tasks" → Instructions; versão 18/11 — a rotina foi criada
pela API e só o Pedro edita na tela; o n8n repete as regras de memória e de "marcar como lido" em todo disparo)

```
You are Pedro Garrido (pedro@poolprofits.com), GHL/automation lead at Pool Profits. For the team and clients you ARE Pedro: first person singular, never "we", never mention Claude/AI. Reply to Pedro himself in Portuguese; to the team/clients in English. To clients the CRM is "Pool Profits CRM" and the app is "Pool Profits" (never GHL, HighLevel or LeadConnector).

The <routine-fire-payload> block below comes from our n8n inbox watch. n8n already removed thanks/FYI/digests and anything I already answered, so every item here needs action. Each item shows [source] [complexity] (easy/medium/complex). Be economical: do only what the items need.

1. git pull on branch claude/fervent-davinci-dpxj0z. CLAUDE.md is loaded automatically: do not re-read it. Read docs/TODO.md (its rules apply to every run). Read other docs only when an item needs them (grep first). For a new sub-account review follow docs/new-account-review.md; for the nightly item follow docs/inbox-watch-routine.md, "Revisao da noite" (steps 1-7).
2. MEMORY CHECK before doing or asking anything: look in the ledger (wb0SlsU03MQ4xdgv) and in Gmail (from:pedro@poolprofits.com newer_than:2d) whether the item was already handled or answered, and check the live state (GHL/ClickUp). Never redo work that is done, and never ask Pedro for something already done.
3. easy items: answer from the thread itself, no repo work unless needed. medium/complex: open the full thread/task, do the full scope and test it end to end (GET + backup before any GHL write; tests only on ZZ TEST copies/contacts, deleted afterwards; never pp_e2e on client accounts; nothing may fire at existing contacts). If a human step is needed (call, live form submit, UI-only setting), do everything else and email pedro@poolprofits.com the exact steps, subject "[Passo seu] ..." (approvals: "[Aprovar] ..."). Files attached anywhere (Basecamp, Gmail, ClickUp) are downloaded by me, never asked to be resent: Basecamp notification e-mails carry a signed storage.app.basecamp.com/.../email/download/ link that curl downloads; if nothing works, ask Pedro, never the team or the client.
4. [pedro_reply] items = Pedro answered one of those emails: "feito/done" -> verify it live, clean up tests, confirm to whoever asked, close the ClickUp task; "aprovado" -> post the approved draft exactly where it belongs.
5. Reply in the same place it was asked (same ClickUp thread/comment, same email thread, internal Basecamp only): short, human. Never say done unless tested. Basecamp/e-mail that does not tag me and is not about the CRM: no reply, just mark it read. If a client can see it: when someone on the team (Frank, Val, Ed) already asked for or approved that message and the context is clear, post it directly (no second approval from Pedro). Otherwise do NOT post: email Pedro the draft ("[Aprovar] ..."). Always email Pedro first for anything ambiguous, new, or sensitive (complaints, prices, blame). Never post a reply less than 5 minutes after the item's received_at.
6. Gmail: after an email/Basecamp item from someone else is handled (or only waits on someone else), mark its thread read (remove UNREAD) so Pedro only sees what needs him. But when you reply to Pedro himself (his [Passo seu]/[Aprovar] threads), mark YOUR reply UNREAD after sending (label_message, labelIds ["UNREAD"]) and never mark that thread read: otherwise he never sees your answer.
7. ClickUp read state: the API exists (scripts/cu_mark_read.py). As the LAST step of every run, after all replies are posted, run: python3 scripts/cu_mark_read.py --sweep . It marks read and clears from the Inbox everything I already answered; LEFT lines are what still needs a reply. Exit code 2 = Pedro's ClickUp session token expired: email Pedro "[Passo seu] ClickUp: renovar o token" with the steps in docs/inbox-watch-routine.md ("Marcar como lido"). Reactions do NOT mark anything as read; do NOT react to every message (Pedro 12/11). Only now and then, when it fits, add one reaction and vary it: thumbsup, white_check_mark or saluting_face. Never react to one that still needs Pedro.
8. Create/update my ClickUp task (list 901422915733) only for real work; close it when tested; one task per subject (merge duplicates).
9. MEMORY of this run, for every item you finish: (a) a row in the ledger "Pedro Inbox Ledger" (wb0SlsU03MQ4xdgv) with the same item_id, status done/needs_pedro, short notes; (b) remove it from docs/TODO.md, or rewrite the step that is left (TODO keeps ONLY open items: the nightly review reads it); (c) one line in docs/execucao-2026-10-27-clearpool-dash.md; (d) commit and push (git pull --no-rebase first; other runs push to the same branch). Trailer: Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>.
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
- A API pública do ClickUp não tem "marcar como lido"; desde 17/11 usamos a API interna do app (`scripts/cu_mark_read.py`,
  seção "Marcar como lido" abaixo).

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

## Respostas do guia do CRM (10/11)
- O "Send to Pedro" do guia manda "[CRM Guide] <cliente> sent their review" de pedro@ para pedro@ (cc Frank). O `Prepare`
  ignorava e-mail do próprio Pedro que não fosse "Re:", então a resposta da Corolla (17h46 UTC) nunca chegou à rotina.
  Agora vira item `crm_guide`: a rotina aplica o que o cliente pediu (textos → `config/<cliente>_wording.json`; decisões
  sim/não → fluxos; tarefas dele → comentário na tarefa do cliente) e manda ao Pedro o que precisa de aprovação.

## Limites
- Tokens das outras agências (Pool Duck, BurchTech, Poolheads antiga) e Application Passwords de WordPress só funcionam
  na sessão da rotina se estiverem nas variáveis do ambiente (TODO, "Tokens fora do chat").
- A auditoria de quinta (19h57) é separada: tarefa agendada desta sessão (`docs/weekly-audit.md`).

## Revisao da noite (item "nightly-tasks-<data>", 21h BRT seg–sex; Pedro 11/11)
O n8n manda esse item uma vez por noite para a mesma rotina "GHL Tasks" (sem rotina separada).
1. **Toda tarefa aberta atribuída ao Pedro em qualquer lista** (16/11: `clickup_filter_tasks` assignees ["me"], todas as
   páginas — lista `901422915733`, "Create GHL Account For Client" `901417290241`, checklists de onboarding do Frank, Paid
   Media Launch; os 3 templates — TEMPLATE V2, "Client Template", HQ antigo — ficam como estão) + DMs/threads do Frank,
   Val e Ed dos últimos 3 dias sem resposta do Pedro: ler descrição/comentários e conferir ao vivo (GHL, ledger, Gmail,
   Basecamp interno). Checklist de onboarding: `scripts/pp_onboarding_check.py --only <conta>`.
1b. Pergunta ao time parada há 2 dias úteis → 1 mensagem só com a lista do que falta + item no e-mail do Pedro. Nunca só
   empurrar o prazo.
2. Feita e conferida → comentar o que foi checado e fechar. Dá para fazer agora → fazer o escopo todo e testar (nunca
   mandar nada a contato existente) e fechar. Depende de outra pessoa → comentar quem/o quê e prazo realista. Só o
   Pedro → fica aberta com prazo realista e vai no e-mail. Nada vencido sem dono; duplicada → fechar a mais nova com link.
3. Reação só de vez em quando (ver 5b), nunca em todas.
4. `docs/TODO.md` só com o aberto; log em `docs/execucao-*.md`; commit/push.
5. UM e-mail "[Passo seu] O que é seu – <data> (revisão da noite)": (a) passos do Pedro, numerados; (b) decisões dele;
   (c) o que foi fechado/adiantado, uma linha cada. Marcar como lidos os [Passo seu] anteriores que ele substitui.
6. **Antes de pôr QUALQUER item no (a) ou (b) — checagem de memória** (Pedro 18/11: a revisão de 17/11 pediu o número da
   Bonneville, que existia desde 16/11, o SMS da Sparkling, já feito, e o "[Aprovar] Justin", enviado 3 h antes):
   - ledger (`wb0SlsU03MQ4xdgv`): linha `done` daquele assunto → não pedir; linha `sent_to_claude` de um `pedro_reply`
     ("aprovado"/"feito") sem `done` depois → fazer agora, não pedir de novo;
   - Gmail: `from:pedro@poolprofits.com newer_than:2d` (respostas e e-mails enviados) — se já respondeu/foi enviado, não pedir;
   - estado ao vivo (GHL/ClickUp): o que o item pede já existe → não pedir; tirar do TODO e contar no (c);
   - `git log --since=yesterday` / `docs/execucao-*.md`.
   Item que passou na checagem e ainda é do Pedro: escrever a prova ("conferi às HH:MM: ainda não existe X").
   **Teste ao vivo pedido ao Pedro** (Pedro 19/11: o e-mail de 18/11 pediu de novo o envio da Reign, feito às 21:41 UTC):
   antes de pedir, procurar o próprio teste no CRM — `GET /forms/submissions` da conta desde o pedido, contato "ZZ TEST
   Pedro"/e-mail ou telefone do Pedro (+55 37 99833-9401), ligação/SMS dele na conversa. Achou → conferir (tags, card,
   aviso), apagar e contar no (c). "A página está no ar" não é prova de que falta o teste.
   **Contato de teste do Pedro marcado spam/dnd numa conta invalida o teste** (Blue Lagoon e Passion, 19/11): apagar o
   contato antigo (backup) antes de pedir ligação/SMS.
8. **Prazos** (Pedro 19/11: duas tarefas venciam no dia e o e-mail não falou delas): seção obrigatória "(d) Prazos" no
   e-mail com TODA tarefa do Pedro vencida, de hoje e de amanhã (`clickup_filter_tasks` assignees ["me"], due_date_to =
   amanhã, include_closed false). Para cada uma, ANTES do e-mail: entregar e fechar; ou, se depende de alguém, comentar
   quem/o quê e mudar a data (nunca deixar vencer sem data nova e motivo). No e-mail: uma linha por tarefa com o que foi
   feito (fechada / nova data + motivo / é do Pedro hoje).
7. **Memória de toda rodada** (não só a da noite): quem termina um item, na mesma rodada, (1) grava a linha `done` no ledger,
   (2) tira o item do `docs/TODO.md` (ou atualiza o passo que sobrou), (3) uma linha no `docs/execucao-*.md`, (4) commit.
   O TODO nunca guarda o que já foi feito — é o que a próxima revisão lê.

## Marcar como lido no ClickUp (17/11)
- API pública (v2/v3): nada de read/unread/Inbox (conferido na referência e no feedback board). O app web usa rotas próprias
  no shard do workspace `frontdoor-prod-us-east-2-2.clickup.com` (achadas no JS do app e testadas ao vivo):
  Inbox `…/inbox/v3/workspaces/{ws}/notifications/bundles/{search|read|<id>/clear}`; chat, threads e comentários
  `…/comment-service/v3/workspaces/{ws}/comments/last_read_at` com chave `view` (canal/DM), `comment` (thread) ou `task`.
- Autenticação: só o token da sessão do navegador do Pedro (a chave pk_ da API dá "Auth header missing"). Ele fica como
  network secret do ambiente Default do Claude Code (host acima, `Authorization: Bearer`); o proxy injeta. Teste 17/11:
  Inbox 64 → 8, canal lido, thread lida (2 → 1).
- **Renovar o token** (quando o script sai com 2): Chrome → app.clickup.com logado → F12 → aba Network → F5 → filtro
  `frontdoor` → clicar numa linha → Headers → Request Headers → `authorization` → copiar o que vem depois de "Bearer "
  (começa com `eyJ`). Depois numa sessão do Claude Code: pedir para salvar o token do ClickUp (formulário seguro do host
  `frontdoor-prod-us-east-2-2.clickup.com`, prefixo Bearer). Nunca colar no chat.

## Rotina recusando o disparo (17/11)
- 15h–17h45 BRT: todo disparo voltou 400 `github_repo_access_denied` (GitHub desconectou do claude.ai; o `git fetch` da
  sessão também dava 403 "reconnect your GitHub account"). O n8n rodava, mas ninguém respondia nada e ninguém sabia.
- Agora: nó **"Fire failed? (alert Pedro)"** → **"Email Pedro (routine down)"** depois do "Send to Claude": disparo
  recusado = e-mail "[URGENTE] Rotina parada: N itens sem resposta" na hora (no máximo 1 a cada 2 h enquanto falhar),
  com a causa e o link para reconectar. Os itens não vão para o ledger, então o próximo disparo manda tudo de novo.
- Correção é humana: reconectar o GitHub em claude.ai (link no e-mail).

## Buraco do fim de semana (corrigido 16/11)
O n8n não roda sábado/domingo e olhava só 26 h para trás: na segunda às 9h, tudo de sexta 7h em diante até domingo caía
fora da janela e nunca era captado (3 tarefas que o Frank criou no domingo 15/11 sobre a West Coast ficaram sem resposta).
Além disso: a lista de tarefas atualizadas lia só a 1ª página (100), e a revisão da noite só olhava a lista do Pedro (as
288 subtarefas de onboarding/Paid Media atribuídas a ele nunca entravam). Correções no n8n (versões 16/11): segunda-feira
olha 76 h (tarefas, comentários, chat) e o Gmail 4 dias; o endpoint de tarefas pagina (até 8 páginas); a revisão da noite
cobre todas as listas e as DMs sem resposta; chamadas de comentários em lotes de 15 a cada 12 s (limite ~100/min do
ClickUp), timeout 14 min. Conferido na rodada de 16/11 15h45 UTC: 287 tarefas em 3 páginas, 0 erro de comentário, 2 itens de
sexta 13/11 que tinham ficado de fora captados. O ledger evita repetir item já tratado.

## Cadência (11/11)
- n8n a cada 15 min no turno (9h–12h45), de hora em hora 13h–19h, + 21h (revisão da noite). Capta **na hora** (sem filtro
  de idade em e-mail nem ClickUp) e manda todo item de ação na mesma rodada (sem segurar médios). A regra dos 5 min é da
  rotina: nenhuma resposta a uma pessoa sai antes de 5 min do `received_at` do item (antes o n8n esperava 5 min para
  captar: o "aprovado" das 12h56 só seria visto às 14h).
