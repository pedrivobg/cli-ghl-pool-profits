# Stay Fresh — revisão das automações antes do Zoom com o Frank (28/10)

Frank (27/10): na call com a Stay Fresh algumas automações não dispararam, outras dispararam errado, e cards
"sumiram" ao mudar de etapa. Leitura de hoje (só leitura, nada alterado): 41 workflows, 20 publicados, pipeline
"Pool Leads" com 13 etapas e só 5 cards.

## O teste do Frank (contato "Pool Profits Testv3", tel. dele, 27/10, horário UTC)
- 20:17 form → card em 🆕 New Lead + tags `new lead`, `form fill` ✓ (Website Form Fill To Pipeline).
- 20:35 card → 💰 Quote Sent: o "Quote Sent Follow-up" entrou, mas **espera 1 dia** antes do SMS 1 → na call parece
  que não disparou. O SMS sai hoje ~20:35 UTC para o celular do Frank — o contato já é cliente Won.
- 20:39 card → 🏆 Won - Weekly: Won Stage ✓ (status won, tags, e-mail + SMS 2 min depois). Review Request entrou
  (30 dias). Status won → o card some da visão do board filtrada em "Open".
- Testv1 e Testv2 não existem mais (contatos apagados → os cards foram junto).

## Problemas reais
1. **Sem condição de parada entre os fluxos.** Quote Sent, No Response e No-Show seguem rodando depois que o card
   vai para outra etapa (Won, Scheduled, Lost…), e no fim **movem o card para ❌ Lost (status lost)**: Quote Sent em
   ~5 dias, No Response em ~11, No-Show em 2. Cliente fechado recebe SMS de cobrança de orçamento e o card Won
   "some" para Lost. Hoje só o No-Show tira o contato de outro fluxo (Appointment Confirmation, que é draft).
2. **Re-entry desligado** em Quote Sent, No Response, Lost Stage, Won Stage e Missed New Lead: o mesmo contato
   movido de novo para a etapa não dispara nada (testado em 20/10: 2ª entrada ignorada). Testar com o mesmo contato
   = "não disparou".
3. **Etapas sem automação publicada**: 💬 In Communication (fluxo em draft), 📅 Scheduled (Appointment
   Confirmation em draft e sem gatilho), 🔄 Recurring (Monthly Service Reminder em draft; Recurring Customer Stage
   só põe tag), ❄ Not Qualified e 🆕 New Lead movido à mão (nenhuma). Post-Appointment, Upsell e o IVR em draft.
4. **Esperas** que parecem falha num teste ao vivo: Quote Sent 1 dia, No Response 1 dia, Lost 2 dias, Review
   Request 30 + 14 dias.
5. **Lixo do pipeline antigo**: Booked Appt, In Communications, Lost Lead, Won Customer, Current Customer, DND
   Contact, AdWords Tracking(s) — draft, apontando para pipeline apagada. Current Customer **apaga o card**
   (`remove_opportunity`) se alguém publicar. Mover para uma pasta "Old - do not publish".

## Correção (Pedro OK 28/10)
- **Aplicado 28/10** (`scripts/sf_stop_followups.py`): novo "Stage Changed -> Stop Follow-ups": card entra em Scheduled, In Communication, os 3 Won, Recurring,
  Not Qualified, Lost ou Spam → tira o contato de Missed New Lead, No Response, Quote Sent e No-Show e as tags
  `follow-up`/`no-show`. Testado numa cópia do Quote Sent com esperas de 1 min: card movido para Scheduled ficou lá;
  controle terminou em Lost. Re-entry e textos intocados (backup dos 3 fluxos).
- **Aplicado**: 1º passo de Quote Sent / No Response / No-Show tira dos outros follow-ups.
- Re-entry ligado nos fluxos de etapa (Quote Sent, Lost, Won, No Response) — decidir no Zoom.
- Etapas sem automação: Frank/Mike decidem o que cada uma faz (publicar os drafts ou não).
- **Feito 19:48 UTC**: contato de teste do Frank tirado do Quote Sent (antes do SMS das 20:35).
