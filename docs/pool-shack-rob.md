# The Pool Shack — pedidos do Rob (Basecamp "Automation Snapshots", Frank 20/10)

Frank pediu para aplicar o feedback do Rob (dono, `owner_first_name` = Robert) nos fluxos e responder 4 dúvidas.
O texto do Rob está no Basecamp (sem acesso daqui): **esperando o Pedro colar a thread**. Aplicar igual à Stay
Fresh: texto exatamente como o cliente escreveu (`config/pool_shack_wording.json` + `pp_wording.py`), teste na Test
Snapshot, depois a conta.

## Estado em 21/10 (`pp_wf_tree.py the-pool-shack`)

Conta quase vazia: 4 contatos (3 de chamada perdida), nenhum cliente; Skimmer não está ligado ao GHL. Fuso
America/Phoenix. Forms de lead pedem só nome/telefone/e-mail (o Service Page pergunta "new customer?").

| Pedido do Rob | Fluxo hoje | Como está |
|---|---|---|
| Missed call follow-up | Missed New Lead - Initial SMS Follow-up (tag `missed call`) | SMS 1 na hora → espera resposta 30 min → SMS 2 + tag `follow-up`; sem janela de horário |
| Quote follow-up | Quote Sent Follow-up (etapa 💰 Quote Sent) | 1 dia → SMS 1 → 2 dias → SMS 2 → 2 dias → Lost; resposta → In Communication; sem janela |
| No-response | No Response Follow-up (tag `follow-up` ou etapa No Response) | 1 dia → SMS 1 → 2 d → SMS 2 → 4 d → SMS 3 → 4 d → Lost; resposta → In Communication; sem janela |
| Lost-stage follow-up | Lost Stage (etapa ❌ Lost) | 2 dias → e-mail de feedback → 90 dias → e-mail check-in; janela seg–sex 9–17 |
| New customer welcome | Won Stage, ramo Weekly | e-mail de boas-vindas + SMS (janela seg–sex 9–17); Repair e Construction só tag/etapa |

## As 4 dúvidas do Frank (análise)

1. **Parar quando responde / já foi contatado / recusou.** Resposta por SMS já encerra as 3 sequências (espera
   por resposta). Não param: ligação de volta, contato feito pela equipe, card movido de etapa (Won/Lost/…).
   Proposta: `stopOnResponse` nos fluxos de follow-up + um fluxo "Stop follow-ups" (etapa nova, ligação atendida
   no número do GHL, tags `spam`/`existing customer`) com *Remove from workflow*. Limite: contato fora do GHL
   (celular pessoal) só se o card for movido.
2. **Horário comercial seg–sex.** Janela de horário (`window`) nos 3 fluxos de SMS de follow-up (Lost/Won/In
   Communication já têm). Decidir com o Rob o SMS imediato de chamada perdida fora do horário ("ligamos em
   instantes" à noite/sábado).
3. **Semanal × reparo × reforma.** Nada identifica o tipo na entrada. Proposta: campo "Service Needed" como
   lista (Weekly / Repair / Remodel) nos forms; nas ligações, quem atende marca no card; os follow-ups ramificam
   pelo campo (sem tipo = texto geral).
4. **Duplicar o Skimmer.** O GHL só fala com cliente semanal no Won Stage (boas-vindas e-mail + SMS) e no Review
   Request (NPS 30 dias depois do Won, nos 3 Won). Monthly Service Reminder, Post-Appointment, Filter Clean e
   Upsell estão em draft. Perguntar se o Skimmer já manda boas-vindas/review; se sim, desligar só no semanal.
