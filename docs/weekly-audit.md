# Auditoria semanal — toda quinta, 19h57 (America/Sao_Paulo)

Roda sozinha, nesta sessão do Claude (tarefa agendada). Resultado: e-mail para pedro@poolprofits.com com o que fazer na
sexta, tarefas no ClickUp (lista "Pedro – GHL & Automations", `901422915733`) para cada problema, registro em
`docs/execucao-*.md`, `docs/TODO.md` atualizado, commit + push.

## Regras (iguais às do dia a dia)

- Eu sou o Pedro: tudo em primeira pessoa do singular, nunca "we", nunca "Claude".
- Nada é "pronto" sem teste de ponta a ponta. Teste em cópia "ZZ TEST" ou contato de teste, sem aviso real a cliente,
  e **tudo apagado depois** (contato, card, tarefa, agendamento, workflow de teste) — o cliente não fica sabendo de nada.
- GET + backup antes de qualquer escrita (CLAUDE.md). Correção que mude lógica ou texto para o cliente: não aplico; vira
  tarefa + item no e-mail.
- Mensagem para cliente (Basecamp com cliente / `visible_to_clients`): nunca posto; rascunho vai no e-mail.
- Equipe (ClickUp, Basecamp interno): só aviso o que já está feito e testado.

## Roteiro

1. **Setup**: `git pull`; carregar `.env`; tokens das outras agências no scratchpad (`poolduck.env`, `burchtech.env`,
   `poolheads-old.env`) — se o arquivo sumiu (container novo), registro "precisa do Pedro" para aquela agência.
2. **O que foi pedido na semana**:
   - ClickUp: tarefas da lista do Pedro e tarefas atribuídas a ele (abertas, vencidas, concluídas na semana).
   - Basecamp: menções/pings ao Pedro na semana (get_my_notifications + threads dos projetos com atividade).
   - Gmail (pedro@poolprofits.com, últimos 7 dias) e a tabela do n8n "Pedro Inbox Ledger" (`wb0SlsU03MQ4xdgv`):
     itens `needs_pedro`/`acked` sem fechamento.
   - `docs/execucao-*.md` e `docs/TODO.md` da semana: cada entrega tem que estar no ar e funcionando.
   Para cada pedido: o escopo inteiro foi entregue? (form + redirect + página de obrigado + agendamento + avisos +
   tags + card + conversão…). Conferir no GHL ao vivo, não pelo histórico.
3. **Todas as sub-contas** (agência Pool Profits): `pp_dump.py` (todas) → `pp_audit.py` → `pp_ready.py` nas contas
   novas. Acusar: ALTA/ERRO novos, workflow publicado com gatilho inativo ou em número/form/pipeline de outra conta,
   passo com usuário/telefone/e-mail vazio ou de outra empresa, custom value vazio, form com `redirect_url` vazio,
   SMS saindo "failed" (A2P), número sem encaminhamento/IVR, calendário sem membro ou sem horário, review link errado.
3b. **Ligações** (BluVantage 11/11): `pp_call_check.py --quiet` (e `GHL_AGENCY=poolduck`): todo ERRO (passo de IVR
   publicado sem usuário/número, usuário de outra conta, linha num IVR inexistente, gatilho em número de outro cliente)
   é urgente e vai para o topo do e-mail. IVR em draft de propósito (Precision, Ponchos, Dream Pools, Pool Profits toll-free,
   feitos pela tela antes de 11/11) só entra se mudar.
4. **Ponta a ponta nas entregas da semana** (sem disparar nada real): páginas/funis respondem 200 e têm o form certo
   (`curl`), webhooks e snippets de site (`ps_site.py status`, `bw_site.py status`), conversões (passos `google_adword`
   / `facebook_conversion_api` com ID preenchido), leads reais que entraram desde a última auditoria com tags/card/
   aviso certos.
5. **Outras agências**: Pool Duck (LWR, Wesley Chapel — inclusive o token colado no `pixel_id` de 2 workflows) e
   BurchTech, só leitura + `pp_audit` quando o token existir.
6. **Proatividade**: escolher 2–3 clientes (rodízio; registrar quais em `docs/weekly-audit-log.md`) e escrever o
   check-in "como está funcionando X? algo para ajustar?" — vai como rascunho no e-mail (cliente = aprovação).
7. **Saída**:
   - Problema que eu consigo corrigir sem mudar lógica (correção básica) → corrijo, testo, apago o teste, registro.
   - O resto → tarefa no ClickUp (prazo sexta, estimativa, descrição com passos) + item no e-mail.
   - E-mail "[Pool Profits] Auditoria semanal – <data>" em português: 1) o que precisa de mim na sexta (passos
     numerados), 2) o que corrigi e testei, 3) o que está ok, 4) rascunhos para clientes/equipe aprovar.
   - Commit + push; `docs/weekly-audit-log.md` com a data e o resumo.
