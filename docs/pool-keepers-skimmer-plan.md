# Pool Keepers × Skimmer — o que dá para integrar (23/11)

Fonte: inventário da Skimmer feito pela extensão (e-mail "[Skimmer] Inventário Pool Keepers", 23/11) + teste no CRM.
Conta viva = BurchTech `KjLd769fprQ2EaBI9Cro` (1.201 contatos, fluxos próprios): tudo nosso entra em draft, publicação combinada.

## Como a Skimmer fala com o CRM hoje
- Integração nativa (Prismatic, polling): GHL → Skimmer = oportunidade num estágio escolhido vira cliente (+ work order
  opcional) a cada 15 min; contatos criados/editados a cada 30 min. Skimmer → GHL = clientes alterados 1×/dia; **atividade
  vira nota no contato a cada hora**. Zapier: só "novo cliente" como gatilho. API pública: Enterprise; webhooks não existem.
- Notas reais na conta (lidas 23/11) começam com um código fixo: `WorkOrderFinished`, `WorkOrderScheduled`, `InvoicePaid`,
  `CustomerMarkedPastDue` (com "Reason: Invoice N overdue"), `CustomerAdded` (com lead source), `CustomerStatusChanged`
  ("…changed to Active/Inactive"), `RouteAssignmentUpdated`.
- **Testado na Test Snapshot (23/11)**: gatilho de workflow `note_add` dispara com nota criada pela API; `{{note.body}}` traz o
  texto inteiro da nota (copiado para um campo e lido de volta). Teste apagado.

## Automações possíveis (sem API/Zapier) — gatilho "Note Added" + if/else no texto
1. `WorkOrderFinished` → Review Request (gate de nota) — só se a Skimmer parar de pedir nota (service feedback ligado hoje).
2. `CustomerAdded` / `CustomerStatusChanged … Active` → tag `existing customer` (+ tira das sequências de lead) e card Won.
3. `CustomerStatusChanged … Inactive` → Lost / reativação em 30–60 dias.
4. `CustomerMarkedPastDue` → aviso interno (a Skimmer já cobra o cliente por e-mail/SMS: não duplicar).
5. `WorkOrderScheduled` → nada ao cliente (Skimmer já manda), só tirar do follow-up de orçamento.

## Decisões do Nathan antes de ligar
- Quem pede avaliação: Skimmer (service feedback, privado) ou CRM (gate → Google). Não os dois.
- Mensagens de serviço (On My Way, Finished, Invoice, Quote) ficam na Skimmer; o CRM não repete.
- Escopo do sync GHL → Skimmer (tela Integrations Center → GoHighLevel → Configure, não legível pela extensão): só o estágio
  Won, nunca todos os contatos (senão lead frio vira cliente e recebe SMS de serviço).
