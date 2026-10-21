# The Pool Shack — pedidos do Rob (Basecamp "Automation Snapshots", Frank 20/10)

Frank pediu para aplicar o feedback do Rob (dono, `owner_first_name` = Robert) nos fluxos e responder 4 dúvidas.
Thread colada pelo Pedro em 21/10. **Aplicado em 21/10** (`scripts/pp_pool_shack_rob.py` estrutura,
`config/pool_shack_wording.json` + `pp_wording.py` textos; testado antes na Test Snapshot).

## Antes das mudanças (21/10 de manhã, `pp_wf_tree.py the-pool-shack`)

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

## O que foi feito (21/10)

| Rob pediu | Feito |
|---|---|
| Missed call: texto dele; 2º contato no próximo dia útil | SMS 1 = texto do Rob, literal. Espera resposta 1 dia (era 30 min) → espera horário comercial → SMS 2 (texto novo, geral) |
| Quote Sent: manter texto e tempo; não ir para Lost sozinho | Textos iguais; saídas para Lost no fim tiradas; SMS 1 e 2 em horário comercial |
| No Response: texto geral, sem urgência | 3 SMS novos (serviço, reparo/instalação, reforma, comercial; sem "spots filling up"); horário comercial |
| Lost: não presumir outra empresa | 2 e-mails reescritos ("adiou, mudou de ideia ou outra coisa"); 90 dias mantidos |
| Boas-vindas por tipo de cliente | Semanal mantido (Rob gostou); Repairs/Installs e Construction ganharam e-mail + SMS próprios |
| Parar quando responde / já falamos / recusou | Workflow novo **Stop Follow-ups** (02 Lead Nurturing): resposta em qualquer canal ou card indo para In Communication, Quote Sent, No Response, Won, Recurring ou Lost tira o contato das sequências que não valem mais |
| Só horário comercial seg–sex | Espera "Business hours (Mon-Fri 9-5)" antes de cada SMS de rotina (fuso da conta, Arizona) |

Teste na Test Snapshot (contatos de teste, workflow TMP como alvo, tudo apagado depois): card → Won Weekly tirou o
contato da sequência; o controle continuou; card → Quote Sent pegou o ramo certo (não tirou o que não devia);
Won Repair mandou o e-mail novo. Resposta do cliente: a API não simula mensagem recebida (401) — o gatilho é o mesmo
"Customer Replied" que já roda no "SMS Customer Reply to pipeline". Na Pool Shack: 11/11 textos conferidos no GHL.
Limites para o Frank: contato fora do GHL (celular pessoal) só para as sequências se o card for movido; o tipo de
serviço do lead não vem sozinho na ligação (proposta das tags universais resolve).
Achado antigo (fora do pedido): "AdWords Form - New Lead" escuta um form que não existe mais na conta.
