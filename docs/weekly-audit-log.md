# Auditoria semanal — registro

## 05/11/2026 (qui)

- **Contas**: 64 da Pool Profits (dump + `pp_audit`), 10 da Pool Duck, 2 da BurchTech. Bug corrigido em `_common.py`: com
  `GHL_AGENCY` o `DUMP` ia para `dump/` (11 pastas Pool Duck/BurchTech misturadas, movidas para `dump/<agência>`).
- **Corrigido e testado**: Clear Pool IVR (ligação real atendida de hoje → SMS certo); Stay Fresh (6 cards + filtro STOP,
  `sf_stop_guard.py`); Bahama Blue (missed call no IVR + 2 fluxos de outras contas em draft); `pp_fix` em Wrigley,
  Sunwave, YardSpring, Precision, Simple, SwimReady, Signature, Clean Co, Corolla, Aqua Clear (tarefas sem responsável,
  merge fields, link de agendamento sem horário → "responda/ligue"); Corolla `a2p_verification_number`; Aqua Clear link de
  review da Clear Pool → o dela; YardSpring/Corolla/Aqua Clear 3 SMS com link de calendário sem membro.
- **Ao vivo ok**: páginas da semana (Poolheads obrigado, NorTex promo, LWR comercial/Google/FB, Pool Shack contato) = 200;
  snippets Pool Shack e Bluewater no ar; leads novos desde 29/10 com tag de origem e card (exceto Southern, 1 caso);
  contatos novos sem tag = spam de eleição (Sunwave, Reign).
- **Check-in (rodízio)**: Clear Pool Tucson (Derek), NorTex (Fareed), The Pool Shack (Rob) — rascunhos no e-mail.
- Tarefas novas: 86bcz86jw (contas no snapshot antigo), 86bcz86m8 (Southern lead sem card), 86bcz86nd (Pool Duck LWR/WC).

## 12/11/2026 (qui)

- **Contas**: 67 da Pool Profits (dump `--all` + `pp_audit` + `pp_fleet_check` + `pp_call_check`), Pool Duck (LWR, Odessa, WC) e
  BurchTech (Pool Keepers, Bluewater).
- **Corrigido**: BluVantage AdWords Call In sem gatilho desde 11/11 (recriado + 2 cards); Friendly Business Name em 4 contas
  (Review Request); Capital No Response duplicado; sobra ZZ TEST na Ekahi (minha). Trava nova no `pp_mirror` (não cria o que
  já existe ao vivo).
- **Check-in (rodízio)**: Precision (Dane), Sunwave (Davey), Bahama Blue (Andy) — rascunhos no e-mail.
- Tarefas novas: 86bd2t1kt (Southern leads sem card), 86bd2t1mq (Application Passwords); comentários em 86bd1b3b5 e 86bcz86jw.

## 19/11/2026 (qui; concluída sex 20/11 ~19h30 UTC — a sessão reiniciou no meio)

- **Contas**: 67 da Pool Profits (dump `--all` + `pp_audit` + `pp_fleet_check` + `pp_call_check`), Pool Duck (`pp_call_check` 0 ERRO);
  leads novos 12/11–20/11 em todas as contas de cliente (contatos "new lead" sem card, por contato).
- **Achados → tarefa 86bd5n0h3**: Sunwave Won Stage → 2 etapas inexistentes + Marketing IVR sem usuário; Pool Smart OC
  Current Customer/DND ouvem pipeline inexistente; ABC/Leisure Website Form Fill sem usuário; Orange Tree chat widget
  inexistente; Pool Palooza 3 ligações sem card; Corolla "Bruce Wayne"/"Peter Parker".
- `pp_call_check`: ERRO só em IVR draft de propósito (Dream Pools, Ponchos, Blue Lagoon desde 17/11).
- [Aprovar] parados (cliente vê): West Coast Service Agreement, Cleverblu sticker, Pool Shack Rob.
- **Check-in (rodízio)**: Southern, Stay Fresh, YardSpring — rascunho no e-mail.

## 26/11/2026 (qui)

- **Contas**: 69 da Pool Profits (dump `--all` 6149 chamadas + `pp_audit` + `pp_fleet_check` + `pp_call_check`), Pool Duck (12 contas:
  `pp_call_check` 0 ERRO, `pd_pipeline_audit` = nenhum fluxo publicado no pipeline antigo, todos os cards no "01. Pool Leads"),
  BurchTech (`pp_call_check` 0 ERRO). Scripts novos: `pp_week_leads.py` (leads da semana sem card), `pp_sms_failed.py` (SMS
  bloqueado por A2P/operadora; 30006 = fixo, ignorado).
- **Leads 19–26/11**: 233 na Pool Profits, 4 sem card (Signature spam, BluVantage card apagado pelo cliente, Pool Palooza GBP
  = fluxos do Todd, Wrigley cliente atual); Pool Duck 19, 1 sem card (East Orlando: card criado e apagado às 18:02).
- **SMS bloqueados (`pp_sms_failed.py`, tarefa 86bd772rb)**: 30034 em WP Pools (25 follow-ups; A2P espera DNS go.wppools.com),
  East Orlando (A2P não enviado, sem site), West Coast (brand FAILED), Cleverblu (última falha 21:57 de 25/11, campanha VERIFIED 21:34 →
  conferir o próximo envio). Stay Fresh 3× 30008, Sunwave 1× saldo insuficiente (20/11).
- **Corrigido e testado**: East Orlando missed call → também e-mail ao dono (SMS depende do A2P; ZZ TEST para o Pedro ok, apagado).
  Sunwave "Marketing - IVR" → "Assign to user" sem usuário → David (`sw_ivr_assign.py`, ZZ TEST ok,
  apagado, call_check ok). `pp_audit`: falsos ALTA removidos (formId do Google Lead Form, `message.chatWidgetId`).
- **86bd5n0h3**: #1 Sunwave Won sem efeito (só existe Won Weekly), #2 corrigido, #5 Orange Tree falso positivo (widget existe),
  #6/#7 sem novidade; resta #3/#4 (Frank confirmar Pool Smart / ABC / Leisure) → 27/11.
- **Ao vivo ok**: vigia Basecamp 190 execuções sem erro (post BluVantage 25/11 entrou sozinho); Clear Pool VM de volta ao MP3 do
  Derek; Poolheads Thanksgiving ativo (1 ligação hoje; quem já tinha a tag "missed call" não recebe o SMS de feriado = mesmo
  comportamento do normal); páginas da semana 200 (Passion ChatGPT LP + obrigado, Sparkling obrigado ×2, Clear Pool obrigado,
  poolheadscare.com + /holidays, go.cleverblu.com).
- **Não checado**: snippets Pool Shack/Bluewater (`status` 401 — Application Passwords fora deste container, 86bd2t1mq).
- **Achados**: Pool Duck WC "Facebook - Qualified Lead (Form Fill)" publicado com token no `pixel_id` (desde 03/11, nunca
  avisado) → rascunho para a Val no e-mail. Passion: 19 fluxos em draft desde 17/11 (pedido do Frank, intencional).
- **Check-in (rodízio)**: Passion Pool Care (John), Sparkling Clear (Robert), Simple Pool Care (Nathan Taylor) — rascunhos no e-mail
  "[Pool Profits] Auditoria semanal – 26/11" (enviado ~00h UTC 27/11, não lido), junto com o rascunho do pixel da WC para a Val.
